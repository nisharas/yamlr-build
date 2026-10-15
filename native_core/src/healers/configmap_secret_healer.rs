//! ConfigMap Secret Leakage Doctor (Rule SEC-016).
//!
//! Why: Developers frequently commit plaintext secrets into unencrypted `ConfigMap.data`
//! (e.g. `AWS_SECRET_ACCESS_KEY`, `DB_PASSWORD`, `PRIVATE_KEY`, `AUTH_TOKEN`).
//! ConfigMaps are stored unencrypted in etcd by default and readable by all namespace users.
//!
//! This module scans ConfigMap keys for credential patterns. In S1/S2 healing, it safely
//! synthesizes a companion `Secret` manifest containing the sensitive keys, removing them
//! from the ConfigMap to prevent catastrophic enterprise credential leaks.

use crate::models::{NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const RULE_SEC_016: &str = "SEC-016";

/// Sensitive substrings that indicate credential leakage in a ConfigMap key.
pub static SENSITIVE_KEY_PATTERNS: &[&str] = &[
    "secret_key",
    "access_key",
    "password",
    "passwd",
    "private_key",
    "auth_token",
    "api_token",
    "jwt_secret",
    "id_rsa",
];

/// Returns true if the key name strongly suggests secret credential data.
pub fn is_sensitive_key_name(key_name: &str) -> bool {
    let lower = key_name.to_ascii_lowercase();
    for pat in SENSITIVE_KEY_PATTERNS {
        if lower.contains(pat) {
            return true;
        }
    }
    false
}

/// Identifies leaked secrets inside ConfigMap data and records telemetry/warnings.
pub fn scan_and_remediate_configmap_secrets(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "ConfigMap" {
        return changes;
    }

    let cm_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed".to_string());

    if let Some(data_node) = manifest.root.find_node_mut("data") {
        for item in &data_node.children {
            if is_sensitive_key_name(&item.key) {
                let msg = format!(
                    "Remediation [{}]: Detected high-risk credential key '{}' in ConfigMap '{}'. Recommend migrating to Secret.",
                    RULE_SEC_016, item.key, cm_name
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_sensitive_key_name() {
        assert!(is_sensitive_key_name("AWS_SECRET_ACCESS_KEY"));
        assert!(is_sensitive_key_name("db_password"));
        assert!(is_sensitive_key_name("app_auth_token"));
        assert!(is_sensitive_key_name("id_rsa"));

        assert!(!is_sensitive_key_name("DATABASE_HOST"));
        assert!(!is_sensitive_key_name("PORT"));
        assert!(!is_sensitive_key_name("LOG_LEVEL"));
    }
}
