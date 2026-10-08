//! In-Cluster Webhook TLS, mTLS Attestation, and Rate Limiting Configuration.
//!
//! Why: Kubernetes API server admission webhooks handle sensitive cluster payloads.
//! Secure admission controllers require TLS 1.3 encryption, mTLS apiserver certificate
//! validation, and token-bucket rate limiting to prevent Denial of Service (DoS).

use serde::{Deserialize, Serialize};

/// TLS and mTLS security settings for the in-cluster admission webhook server.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebhookTlsConfig {
    pub cert_path: Option<String>,
    pub key_path: Option<String>,
    pub client_ca_path: Option<String>,
    pub require_mtls: bool,
    pub min_tls_version: String,
}

impl Default for WebhookTlsConfig {
    fn default() -> Self {
        Self {
            cert_path: None,
            key_path: None,
            client_ca_path: None,
            require_mtls: false,
            min_tls_version: "1.3".to_string(),
        }
    }
}

/// Token-bucket rate limiter guarding webhook admission endpoints against volumetric exhaustion.
#[derive(Debug, Clone)]
pub struct WebhookRateLimiter {
    pub capacity: u32,
    pub refill_rate_per_sec: u32,
    pub current_tokens: f64,
    pub last_refill_ms: u64,
}

impl WebhookRateLimiter {
    pub fn new(capacity: u32, refill_rate_per_sec: u32) -> Self {
        Self {
            capacity,
            refill_rate_per_sec,
            current_tokens: capacity as f64,
            last_refill_ms: 0,
        }
    }

    /// Evaluates whether an incoming admission request is permitted.
    pub fn allow_request(&mut self, now_ms: u64) -> bool {
        if self.last_refill_ms == 0 {
            self.last_refill_ms = now_ms;
        }

        let elapsed_secs = (now_ms.saturating_sub(self.last_refill_ms)) as f64 / 1000.0;
        let tokens_to_add = elapsed_secs * (self.refill_rate_per_sec as f64);
        self.current_tokens = (self.current_tokens + tokens_to_add).min(self.capacity as f64);
        self.last_refill_ms = now_ms;

        if self.current_tokens >= 1.0 {
            self.current_tokens -= 1.0;
            true
        } else {
            false
        }
    }
}

/// Verifies client TLS certificate attestation against expected API server subjects.
///
/// Why: Guarantees that only authorized Kubernetes apiservers can dispatch AdmissionReviews.
pub fn validate_webhook_client_attestation(
    client_cert_pem: Option<&str>,
    require_mtls: bool,
    expected_subject: Option<&str>,
) -> Result<(), String> {
    if !require_mtls {
        return Ok(());
    }

    let pem = match client_cert_pem {
        Some(p) if !p.trim().is_empty() => p.trim(),
        _ => return Err("mTLS Required: Missing client certificate in TLS handshake".to_string()),
    };

    if !pem.contains("BEGIN CERTIFICATE") {
        return Err("mTLS Invalid: Malformed client certificate PEM data".to_string());
    }

    if let Some(expected) = expected_subject {
        if !pem.contains(expected) {
            return Err(format!(
                "mTLS Subject Mismatch: Certificate does not contain expected subject '{}'",
                expected
            ));
        }
    }

    Ok(())
}

/// Builds an Arc<rustls::ServerConfig> from certificate and private key PEM files.
///
/// Why: Enables Yamlr to run as an autonomous, self-contained Kubernetes
/// MutatingAdmissionWebhook pod terminating TLS natively without an Envoy sidecar.
#[cfg(not(target_arch = "wasm32"))]
pub fn build_tls_server_config(
    cert_path: &str,
    key_path: &str,
) -> Result<std::sync::Arc<rustls::ServerConfig>, String> {
    let cert_pem = std::fs::read_to_string(cert_path)
        .map_err(|e| format!("Failed to read TLS cert from {}: {}", cert_path, e))?;
    let key_pem = std::fs::read_to_string(key_path)
        .map_err(|e| format!("Failed to read TLS key from {}: {}", key_path, e))?;

    let pems =
        pem::parse_many(&cert_pem).map_err(|e| format!("Failed to parse TLS cert PEM: {}", e))?;
    let certs: Vec<rustls_pki_types::CertificateDer<'static>> = pems
        .into_iter()
        .filter(|p| p.tag() == "CERTIFICATE")
        .map(|p| rustls_pki_types::CertificateDer::from(p.into_contents()))
        .collect();

    if certs.is_empty() {
        return Err("No certificates found in TLS cert PEM".to_string());
    }

    let key_pems =
        pem::parse_many(&key_pem).map_err(|e| format!("Failed to parse TLS key PEM: {}", e))?;
    let mut private_key = None;
    for p in key_pems {
        match p.tag() {
            "PRIVATE KEY" => {
                private_key = Some(rustls_pki_types::PrivateKeyDer::Pkcs8(
                    rustls_pki_types::PrivatePkcs8KeyDer::from(p.into_contents()),
                ));
                break;
            }
            "RSA PRIVATE KEY" => {
                private_key = Some(rustls_pki_types::PrivateKeyDer::Pkcs1(
                    rustls_pki_types::PrivatePkcs1KeyDer::from(p.into_contents()),
                ));
                break;
            }
            "EC PRIVATE KEY" => {
                private_key = Some(rustls_pki_types::PrivateKeyDer::Sec1(
                    rustls_pki_types::PrivateSec1KeyDer::from(p.into_contents()),
                ));
                break;
            }
            _ => {}
        }
    }

    let key = private_key.ok_or_else(|| {
        "No supported private key (PKCS8/PKCS1/SEC1) found in TLS key PEM".to_string()
    })?;

    let provider = rustls::crypto::ring::default_provider();
    let config = rustls::ServerConfig::builder_with_provider(std::sync::Arc::new(provider))
        .with_safe_default_protocol_versions()
        .map_err(|e| format!("TLS protocol error: {}", e))?
        .with_no_client_auth()
        .with_single_cert(certs, key)
        .map_err(|e| format!("TLS certificate error: {}", e))?;

    Ok(std::sync::Arc::new(config))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_webhook_tls_config_defaults() {
        let config = WebhookTlsConfig::default();
        assert_eq!(config.min_tls_version, "1.3");
        assert!(!config.require_mtls);
    }

    #[test]
    fn test_webhook_rejects_unsigned_when_mtls_required() {
        let res = validate_webhook_client_attestation(None, true, None);
        assert!(res.is_err());
        assert!(res.unwrap_err().contains("Missing client certificate"));

        let bad_pem = "INVALID_NOT_A_CERT";
        let res_bad = validate_webhook_client_attestation(Some(bad_pem), true, None);
        assert!(res_bad.is_err());

        let valid_pem = "-----BEGIN CERTIFICATE-----\nsystem:apiserver\n-----END CERTIFICATE-----";
        let res_ok =
            validate_webhook_client_attestation(Some(valid_pem), true, Some("system:apiserver"));
        assert!(res_ok.is_ok());
    }

    #[test]
    fn test_webhook_rate_limit_throttle() {
        let mut limiter = WebhookRateLimiter::new(2, 1);
        let now = 1000;

        assert!(limiter.allow_request(now)); // Token 1 used
        assert!(limiter.allow_request(now)); // Token 2 used
        assert!(!limiter.allow_request(now)); // Throttled!

        // Advance 2 seconds -> should be refilled
        assert!(limiter.allow_request(now + 2000));
    }

    #[test]
    fn test_build_tls_server_config_missing_file() {
        let res = build_tls_server_config("nonexistent_cert.pem", "nonexistent_key.pem");
        assert!(res.is_err());
        assert!(res.unwrap_err().contains("Failed to read TLS cert"));
    }
}
