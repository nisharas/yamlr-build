//! WebAssembly (WASM) Bridge for Yamlr Core Engine.
//!
//! Why: Enables client-side execution in browsers (yamlr.dev playground) and edge runtimes
//! with zero server overhead and 100% privacy (manifests never leave the browser).
//! Operates hermetically without filesystem or OS dependencies.

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

use crate::sharder::native_shard;
use crate::structurer::native_structurize;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WasmScanResult {
    pub rule_id: String,
    pub check_name: String,
    pub message: String,
    pub severity: String,
    pub line_no: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WasmHealResponse {
    pub healed_yaml: String,
    pub changes: Vec<String>,
    pub diff: String,
    pub rules_applied: usize,
}

/// Scans raw YAML content for schema, security, and reliability violations in WebAssembly.
#[cfg_attr(feature = "wasm", wasm_bindgen)]
pub fn wasm_scan(content: &str) -> String {
    let shards = native_shard(content);
    let manifest = native_structurize(shards);
    let mut findings = Vec::new();

    // 1. Audit manifest kind and apiVersion
    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if let Some(violation) = crate::audit_engine::audit_manifest(&api_version, &kind) {
        findings.push(WasmScanResult {
            rule_id: violation.rule_id,
            check_name: violation.check_name,
            message: violation.message,
            severity: violation.severity,
            line_no: violation.line_no,
        });
    }

    // 2. Audit images
    for container in manifest.root.find_nodes_by_key_recursive("image") {
        if let Some(ref img) = container.value {
            if let Some(violation) = crate::audit_engine::audit_image(img) {
                findings.push(WasmScanResult {
                    rule_id: violation.rule_id,
                    check_name: violation.check_name,
                    message: violation.message,
                    severity: violation.severity,
                    line_no: violation.line_no,
                });
            }
        }
    }

    serde_json::to_string(&findings).unwrap_or_else(|_| "[]".to_string())
}

/// Surgically heals raw YAML content in WebAssembly, preserving comments and formatting.
#[cfg_attr(feature = "wasm", wasm_bindgen)]
pub fn wasm_heal(content: &str) -> String {
    let (healed_yaml, changes) = crate::cli::heal_cmd::heal_manifest_string(content);
    let diff = compute_unified_diff(content, &healed_yaml);

    let response = WasmHealResponse {
        rules_applied: changes.len(),
        changes,
        healed_yaml,
        diff,
    };

    serde_json::to_string(&response).unwrap_or_else(|_| "{}".to_string())
}

/// Generates a unified diff between original and healed manifests in WebAssembly.
#[cfg_attr(feature = "wasm", wasm_bindgen)]
pub fn wasm_diff(original: &str, healed: &str) -> String {
    compute_unified_diff(original, healed)
}

/// Returns the engine version identifier for WebAssembly bindings.
#[cfg_attr(feature = "wasm", wasm_bindgen)]
pub fn wasm_version() -> String {
    format!("{}-wasm", env!("CARGO_PKG_VERSION"))
}

fn compute_unified_diff(original: &str, healed: &str) -> String {
    let orig_lines: Vec<&str> = original.lines().collect();
    let healed_lines: Vec<&str> = healed.lines().collect();

    let mut diff = String::new();
    diff.push_str("--- original.yaml\n");
    diff.push_str("+++ healed.yaml\n");

    let max_len = orig_lines.len().max(healed_lines.len());
    let mut hunk_header_added = false;

    for i in 0..max_len {
        let orig = orig_lines.get(i).copied();
        let heal = healed_lines.get(i).copied();

        match (orig, heal) {
            (Some(o), Some(h)) if o != h => {
                if !hunk_header_added {
                    diff.push_str("@@ -1 +1 @@\n");
                    hunk_header_added = true;
                }
                diff.push_str(&format!("-{}\n", o));
                diff.push_str(&format!("+{}\n", h));
            }
            (Some(o), None) => {
                diff.push_str(&format!("-{}\n", o));
            }
            (None, Some(h)) => {
                diff.push_str(&format!("+{}\n", h));
            }
            (Some(o), Some(_)) => {
                diff.push_str(&format!(" {}\n", o));
            }
            (None, None) => {}
        }
    }

    diff
}

static DYNAMIC_SCHEMAS: std::sync::RwLock<Option<std::collections::HashMap<String, String>>> =
    std::sync::RwLock::new(None);

/// Dynamically registers a Kubernetes OpenAPI schema JSON string for a specific version in WebAssembly memory.
#[cfg_attr(feature = "wasm", wasm_bindgen)]
pub fn wasm_load_schema(version: &str, schema_json: &str) -> bool {
    if version.trim().is_empty() || schema_json.trim().is_empty() {
        return false;
    }
    if serde_json::from_str::<serde_json::Value>(schema_json).is_err() {
        return false;
    }
    if let Ok(mut lock) = DYNAMIC_SCHEMAS.write() {
        let map = lock.get_or_insert_with(std::collections::HashMap::new);
        map.insert(version.to_string(), schema_json.to_string());
        true
    } else {
        false
    }
}

/// Checks if a schema is loaded in WebAssembly memory for a given version.
#[cfg_attr(feature = "wasm", wasm_bindgen)]
pub fn wasm_has_schema(version: &str) -> bool {
    if let Ok(lock) = DYNAMIC_SCHEMAS.read() {
        if let Some(ref map) = *lock {
            return map.contains_key(version);
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_wasm_version() {
        assert_eq!(wasm_version(), "0.1.0-wasm");
    }

    #[test]
    fn test_wasm_load_schema() {
        assert!(!wasm_has_schema("1.31"));
        let valid_json =
            r#"{"openapi": "3.0.0", "info": {"title": "k8s 1.31", "version": "v1.31.0"}}"#;
        assert!(wasm_load_schema("1.31", valid_json));
        assert!(wasm_has_schema("1.31"));
        assert!(!wasm_load_schema("1.31", "invalid json"));
    }

    #[test]
    fn test_wasm_scan_detects_violations() {
        let bad_yaml = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n        - name: web\n          image: nginx:latest\n";
        let res_json = wasm_scan(bad_yaml);
        assert!(res_json.contains("OPS-002"));
    }

    #[test]
    fn test_wasm_heal_repairs_and_returns_diff() {
        let bad_yaml = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  annotations:\n    yamlr.dev/pin-tags: \"true\"\nspec:\n  template:\n    spec:\n      containers:\n        - name: web\n          image: nginx:latest\n";
        let res_json = wasm_heal(bad_yaml);
        let parsed: WasmHealResponse = serde_json::from_str(&res_json).unwrap();
        assert!(parsed.rules_applied > 0);
        assert!(parsed.diff.contains("+++ healed.yaml"));
    }

    #[test]
    fn test_wasm_diff_computation() {
        let orig = "line1\nline2\n";
        let healed = "line1\nline2_healed\n";
        let diff = wasm_diff(orig, healed);
        assert!(diff.contains("-line2"));
        assert!(diff.contains("+line2_healed"));
    }
}
