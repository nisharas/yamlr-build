//! Cryptographic manifest signing and signature verification.
//!
//! Why: Enables GitOps admission integrity by signing Kubernetes manifests
//! with HMAC-SHA256 annotations or RSA-256 JWT signatures to detect
//! unauthorized tampering before cluster deployment.

use chrono::Utc;
use hex;
use hmac::{Hmac, Mac};
#[cfg(not(target_arch = "wasm32"))]
use jsonwebtoken::{decode, encode, Algorithm, DecodingKey, EncodingKey, Header, Validation};
use regex::Regex;
use serde_json::Value as JsonValue;
use sha2::{Digest, Sha256};

#[cfg(not(target_arch = "wasm32"))]
use crate::security::licensing::Claims;

type HmacSha256 = Hmac<Sha256>;

/// Strips all signature annotations from manifest content to produce
/// canonical representation for signing and verification.
pub fn strip_manifest_signatures(content: &str) -> String {
    let mut result_lines = Vec::new();
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("yamlr.io/signature:")
            || trimmed.starts_with("yamlr.io/signed-at:")
            || trimmed.starts_with("yamlr.dev/signature:")
            || trimmed.starts_with("yamlr.dev/signed-at:")
        {
            continue;
        }
        result_lines.push(line);
    }
    result_lines.join("\n")
}

/// Normalizes manifest content into canonical key-sorted representation for deterministic HMAC computation.
/// Strips yamlr signature annotations and prunes empty annotations mapping.
pub fn canonicalize_manifest_for_hmac(content: &str) -> String {
    if let Ok(mut doc) = serde_yaml::from_str::<JsonValue>(content) {
        if let Some(metadata) = doc.get_mut("metadata") {
            if let Some(annotations) = metadata.get_mut("annotations") {
                if let Some(map) = annotations.as_object_mut() {
                    map.remove("yamlr.io/signature");
                    map.remove("yamlr.io/signed-at");
                    map.remove("yamlr.dev/signature");
                    map.remove("yamlr.dev/signed-at");
                }
            }
            let is_empty_ann = metadata
                .get("annotations")
                .and_then(|a| a.as_object())
                .map_or(false, |m| m.is_empty());
            if is_empty_ann {
                if let Some(meta_map) = metadata.as_object_mut() {
                    meta_map.remove("annotations");
                }
            }
        }
        if let Ok(serialized) = serde_json::to_string(&doc) {
            return serialized;
        }
    }
    strip_manifest_signatures(content)
}

/// Computes the HMAC-SHA256 hex digest of a canonical manifest string.
pub fn compute_manifest_hmac(canonical_content: &str, secret_key: &str) -> String {
    let mut mac = HmacSha256::new_from_slice(secret_key.as_bytes())
        .expect("HMAC-SHA256 accepts keys of any size");
    mac.update(canonical_content.trim().as_bytes());
    hex::encode(mac.finalize().into_bytes())
}

/// Extracts any embedded signature from manifest annotations.
pub fn extract_manifest_signature(content: &str) -> Option<String> {
    for line in content.lines() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("yamlr.io/signature:") {
            let sig = rest.trim().trim_matches('"').trim_matches('\'');
            if !sig.is_empty() {
                return Some(sig.to_string());
            }
        }
        if let Some(rest) = trimmed.strip_prefix("yamlr.dev/signature:") {
            let sig = rest.trim().trim_matches('"').trim_matches('\'');
            if !sig.is_empty() {
                return Some(sig.to_string());
            }
        }
    }
    None
}

/// Signs manifest content with HMAC-SHA256, embedding `yamlr.io/signature`
/// and `yamlr.io/signed-at` annotations.
pub fn sign_manifest_hmac(content: &str, secret_key: &str) -> String {
    let canonical = canonicalize_manifest_for_hmac(content);
    let signature = compute_manifest_hmac(&canonical, secret_key);
    let timestamp = Utc::now().to_rfc3339();

    inject_signature_annotations(content, &signature, &timestamp)
}

/// Injects or updates signature annotations in manifest YAML string.
fn inject_signature_annotations(content: &str, signature: &str, timestamp: &str) -> String {
    let stripped = strip_manifest_signatures(content);
    let sig_lines = format!(
        "    yamlr.dev/signature: \"{}\"\n    yamlr.dev/signed-at: \"{}\"",
        signature, timestamp
    );

    // If "annotations:" already exists under metadata
    let ann_re = Regex::new(r"(?m)^(\s*)annotations:\s*$").unwrap();
    if let Some(mat) = ann_re.find(&stripped) {
        let prefix = &stripped[..mat.end()];
        let suffix = &stripped[mat.end()..];
        return format!("{}\n{}{}", prefix, sig_lines, suffix);
    }

    // If "metadata:" exists but no annotations
    let meta_re = Regex::new(r"(?m)^(\s*)metadata:\s*$").unwrap();
    if let Some(mat) = meta_re.find(&stripped) {
        let prefix = &stripped[..mat.end()];
        let suffix = &stripped[mat.end()..];
        return format!("{}\n  annotations:\n{}{}", prefix, sig_lines, suffix);
    }

    // If no metadata section exists
    format!(
        "{}\nmetadata:\n  annotations:\n{}\n",
        stripped.trim_end(),
        sig_lines
    )
}

/// Verifies manifest HMAC-SHA256 signature against content excluding annotations.
pub fn verify_manifest_hmac(content: &str, secret_key: &str) -> bool {
    let extracted_sig = match extract_manifest_signature(content) {
        Some(sig) => sig,
        None => return false,
    };

    let canonical = canonicalize_manifest_for_hmac(content);
    let expected_sig = compute_manifest_hmac(&canonical, secret_key);

    extracted_sig.eq_ignore_ascii_case(&expected_sig)
}

/// Signs a manifest string with RS256 JWT (legacy compatible).
#[cfg(not(target_arch = "wasm32"))]
pub fn sign_manifest_rsa(content: &str, private_key_pem: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    let hash_hex = hex::encode(hasher.finalize());

    let claims = Claims {
        sub: "manifest-signature".to_string(),
        exp: 2147483647,
        tier: hash_hex,
    };

    match EncodingKey::from_rsa_pem(private_key_pem.as_bytes()) {
        Ok(k) => match encode(&Header::new(Algorithm::RS256), &claims, &k) {
            Ok(token) => token,
            Err(e) => format!("ERR_ENCODE_FAILED: {}", e),
        },
        Err(_) => "ERR_INVALID_KEY".to_string(),
    }
}

#[cfg(target_arch = "wasm32")]
pub fn sign_manifest_rsa(_content: &str, _private_key_pem: &str) -> String {
    "ERR_NOT_SUPPORTED_ON_WASM".to_string()
}

/// Verifies a signed manifest with RS256 JWT (legacy compatible).
#[cfg(not(target_arch = "wasm32"))]
pub fn verify_manifest_rsa(content: &str, signature: &str, public_key_pem: &str) -> bool {
    let mut validation = Validation::new(Algorithm::RS256);
    validation.validate_exp = true;

    let key = DecodingKey::from_rsa_pem(public_key_pem.as_bytes());
    if let Ok(k) = key {
        if let Ok(token_data) = decode::<Claims>(signature, &k, &validation) {
            let mut hasher = Sha256::new();
            hasher.update(content.as_bytes());
            let current_hash = hex::encode(hasher.finalize());
            return token_data.claims.tier == current_hash;
        }
    }
    false
}

#[cfg(target_arch = "wasm32")]
pub fn verify_manifest_rsa(_content: &str, _signature: &str, _public_key_pem: &str) -> bool {
    false
}

/// Cryptographically signs a manifest string.
/// If `key` is an RSA PEM key, returns the RS256 JWT signature token.
/// Otherwise, embeds `yamlr.io/signature` and `yamlr.io/signed-at` using HMAC-SHA256.
pub fn native_sign_manifest(content: &str, key: &str) -> String {
    if key.trim().starts_with("-----BEGIN") {
        sign_manifest_rsa(content, key)
    } else {
        sign_manifest_hmac(content, key)
    }
}

/// Verifies a manifest signature.
/// If `public_key_pem` is provided, performs RSA JWT verification.
/// Otherwise, performs HMAC-SHA256 signature verification on embedded annotations.
pub fn native_verify_manifest(
    content: &str,
    signature_or_secret: &str,
    public_key_pem: Option<&str>,
) -> bool {
    if let Some(pubkey) = public_key_pem {
        if !pubkey.trim().is_empty() {
            return verify_manifest_rsa(content, signature_or_secret, pubkey);
        }
    }
    verify_manifest_hmac(content, signature_or_secret)
}
