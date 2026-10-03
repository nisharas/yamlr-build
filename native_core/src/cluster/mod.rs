//! Kubernetes Cluster Integration and Admission Controllers.
//!
//! Why: In-cluster admission control, mutating webhook engines, and cluster version detection. Strictly < 500 lines.

pub mod tls_config;
pub mod webhook;

pub use tls_config::{validate_webhook_client_attestation, WebhookRateLimiter, WebhookTlsConfig};
#[cfg(not(target_arch = "wasm32"))]
pub use tls_config::build_tls_server_config;
pub use webhook::handle_admission_review;

use serde_json::Value;
use std::env;
use std::process::Command;

/// Resolves K8s cluster version with fallbacks.
pub fn native_detect_cluster_version() -> String {
    // 1. Explicit Environment Override
    if let Ok(env_ver) = env::var("YAMLR_K8S_VERSION") {
        let clean = env_ver.trim();
        if !clean.is_empty() {
            return clean.to_string();
        }
    }

    // 2. Try 'kubectl version -o json'
    let output = Command::new("kubectl")
        .args(["version", "--client", "-o", "json"])
        .output();

    if let Ok(out) = output {
        if out.status.success() {
            if let Ok(stdout) = std::str::from_utf8(&out.stdout) {
                if let Some(parsed) = parse_kubectl_version_json(stdout) {
                    return parsed;
                }
            }
        }
    }

    // 3. Check for In-Cluster Environment
    if env::var("KUBERNETES_SERVICE_HOST").is_ok() {
        return "1.31".to_string();
    }

    // 4. Default Enterprise Standard
    "1.30".to_string()
}

/// Parses kubectl JSON output safely into "Major.Minor" format.
pub fn parse_kubectl_version_json(json_str: &str) -> Option<String> {
    let val: Value = serde_json::from_str(json_str).ok()?;

    // Check clientVersion or serverVersion
    let ver_obj = val
        .get("clientVersion")
        .or_else(|| val.get("serverVersion"))
        .or(Some(&val))?;

    let major_raw = ver_obj.get("major").and_then(|v| v.as_str())?;
    let minor_raw = ver_obj.get("minor").and_then(|v| v.as_str())?;

    let major: String = major_raw.chars().filter(|c| c.is_ascii_digit()).collect();
    let minor: String = minor_raw.chars().filter(|c| c.is_ascii_digit()).collect();

    if !major.is_empty() && !minor.is_empty() {
        Some(format!("{}.{}", major, minor))
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_kubectl_version_json_valid() {
        let sample = r#"{
            "clientVersion": {
                "major": "1",
                "minor": "30+",
                "gitVersion": "v1.30.2"
            }
        }"#;
        assert_eq!(parse_kubectl_version_json(sample), Some("1.30".to_string()));
    }

    #[test]
    fn test_parse_kubectl_version_json_direct() {
        let sample = r#"{
            "major": "1",
            "minor": "29"
        }"#;
        assert_eq!(parse_kubectl_version_json(sample), Some("1.29".to_string()));
    }

    #[test]
    fn test_parse_kubectl_version_json_invalid() {
        assert_eq!(parse_kubectl_version_json("not json"), None);
        assert_eq!(parse_kubectl_version_json("{}"), None);
    }
}
