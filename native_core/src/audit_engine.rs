use crate::models::*;
use lazy_static::lazy_static;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DetectorDefinition {
    pub id: String,
    pub category: String,
    pub name: String,
    pub severity: String,
    pub rationale: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ForensicCatalog {
    pub catalog_version: String,
    pub total_detectors: usize,
    pub detectors: Vec<DetectorDefinition>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ApiDeprecation {
    pub deprecated_api: String,
    pub replacement_api: String,
    pub removed_in_version: String,
    pub kind: String,
    pub severity: String,
    pub migration_notes: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DeprecationDatabase {
    pub apis: Vec<ApiDeprecation>,
}

lazy_static! {
    static ref CATALOG: ForensicCatalog = {
        let data = include_str!("../catalog/forensic_catalog.json");
        serde_json::from_str(data).unwrap_or_else(|e| {
            eprintln!("[ERROR] Failed to parse forensic_catalog.json: {}", e);
            ForensicCatalog {
                catalog_version: "0.1.0-fallback".to_string(),
                total_detectors: 0,
                detectors: Vec::new(),
            }
        })
    };

    static ref DEPRECATIONS: DeprecationDatabase = {
        // We will embed the comprehensive K8s deprecation database
        let data = include_str!("../catalog/k8s_deprecations.json");
        serde_json::from_str(data).unwrap_or_else(|e| {
            eprintln!("[ERROR] Failed to parse k8s_deprecations.json: {}", e);
            DeprecationDatabase { apis: Vec::new() }
        })
    };

    static ref CIS_MAPPING: serde_json::Value = {
        let data = include_str!("../catalog/cis_benchmark_mapping.json");
        serde_json::from_str(data).unwrap_or_else(|e| {
            eprintln!("[ERROR] Failed to parse cis_benchmark_mapping.json: {}", e);
            serde_json::json!({})
        })
    };
}

pub struct ForensicRegistry;

impl ForensicRegistry {
    pub fn get_detector(id: &str) -> Option<DetectorDefinition> {
        CATALOG.detectors.iter().find(|d| d.id == id).cloned()
    }

    pub fn get_all_detectors() -> Vec<DetectorDefinition> {
        CATALOG.detectors.clone()
    }

    pub fn get_cis_tag(detector_id: &str) -> Option<String> {
        CIS_MAPPING
            .pointer(&format!("/rules/{}/cis_id", detector_id))
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
    }
}

pub fn get_catalog() -> &'static ForensicCatalog {
    &CATALOG
}

pub fn get_deprecations() -> &'static DeprecationDatabase {
    &DEPRECATIONS
}

pub fn native_run_audit(content: &str) -> Vec<IntegrityViolation> {
    let mut violations = Vec::new();
    if let Some(v) = audit_secret_leakage("Manifest", content) {
        violations.push(v);
    }
    for info in &DEPRECATIONS.apis {
        if content.contains(&info.deprecated_api) && content.contains(&info.kind) {
            violations.push(IntegrityViolation {
                check_name: "API-DEPRECATION".to_string(),
                message: format!(
                    "{}/{} is deprecated and removed in {}. {}",
                    info.deprecated_api, info.kind, info.removed_in_version, info.migration_notes
                ),
                severity: info.severity.clone(),
                rule_id: "DEP-001".to_string(),
                line_no: 0,
            });
        }
    }
    if content.contains(":latest") {
        if let Some(v) = audit_image(":latest") {
            violations.push(v);
        }
    }
    violations
}

pub fn audit_manifest(api_version: &str, kind: &str) -> Option<IntegrityViolation> {
    // Check for exact or case-insensitive matches
    for info in &DEPRECATIONS.apis {
        if info.deprecated_api.to_lowercase() == api_version.to_lowercase()
            && info.kind.to_lowercase() == kind.to_lowercase()
        {
            return Some(IntegrityViolation {
                check_name: "PRO-001".to_string(), // API Deprecation Prediction
                message: format!(
                    "{}/{} is deprecated and removed in {}. {}",
                    info.deprecated_api, kind, info.removed_in_version, info.migration_notes
                ),
                severity: info.severity.clone(),
                rule_id: "PRO-001".to_string(),
                line_no: 0,
            });
        }
    }
    None
}

pub fn audit_image(image: &str) -> Option<IntegrityViolation> {
    // Image Immutability Auditing
    if image.to_lowercase().ends_with(":latest") || !image.contains(':') {
        return Some(IntegrityViolation {
            check_name: "IMAGE-IMMUTABILITY".to_string(),
            message: format!(
                "Image '{}' utilizes a mutable tag (:latest or none). Use a specific digest or version tag for production stability.",
                image
            ),
            severity: "HIGH".to_string(),
            rule_id: "OPS-002".to_string(),
            line_no: 0,
        });
    }
    None
}

pub fn audit_resource_ratio(cpu: &str, mem: &str) -> Option<IntegrityViolation> {
    // Burst-OOM Prevention
    // Simple heuristic: If CPU > 2 cores but Mem < 512Mi, it's a 'Burst OOM' risk.
    let cpu_val = if cpu.ends_with('m') {
        cpu.trim_end_matches('m').parse::<f64>().unwrap_or(0.0) / 1000.0
    } else {
        cpu.parse::<f64>().unwrap_or(0.0)
    };

    let mem_val = if mem.ends_with("Mi") {
        mem.trim_end_matches("Mi").parse::<f64>().unwrap_or(0.0)
    } else if mem.ends_with("Gi") {
        mem.trim_end_matches("Gi").parse::<f64>().unwrap_or(0.0) * 1024.0
    } else {
        mem.parse::<f64>().unwrap_or(0.0)
    };

    if cpu_val > 2.0 && mem_val < 512.0 {
        return Some(IntegrityViolation {
            check_name: "PROPORTIONAL-RESOURCE-HAZARD".to_string(),
            message: format!("Burst OOM Risk: High CPU ({} cores) with low Memory ({} Mi). Processing spikes may cause OOMKilled events.", cpu_val, mem_val),
            severity: "WARNING".to_string(),
            rule_id: "REL-010".to_string(),
            line_no: 0,
        });
    }
    None
}

pub fn audit_flow_style(key: &str) -> Option<IntegrityViolation> {
    // Flow-Style Auditing
    Some(IntegrityViolation {
        check_name: "FLOW-STYLE-DETECTED".to_string(),
        message: format!(
            "Maintainability: Field '{}' utilizes flow-style YAML ({{...}} or [...]). Convert to block-style for better production auditability.",
            key
        ),
        severity: "INFO".to_string(),
        rule_id: "BST-000".to_string(), // General Style
        line_no: 0,
    })
}

pub fn audit_immutable_fields(kind: &str, field_path: &str) -> Option<IntegrityViolation> {
    // Immutability-Safe Auditing
    let is_immutable = match kind {
        "Deployment" | "StatefulSet" | "DaemonSet" => field_path == "spec.selector",
        "Service" => field_path == "spec.clusterIP" || field_path == "spec.type",
        "Job" => field_path == "spec.selector" || field_path == "spec.template",
        _ => false,
    };

    if is_immutable {
        Some(IntegrityViolation {
            check_name: "IMMUTABLE-FIELD-MUTATION".to_string(),
            severity: "CRITICAL".to_string(),
            message: format!(
                "Field '{}' is immutable for Kind '{}'. Mutations will cause deployment failure.",
                field_path, kind
            ),
            rule_id: "OPS-001".to_string(),
            line_no: 0,
        })
    } else {
        None
    }
}

pub fn audit_selector_match(
    kind: &str,
    selector: &std::collections::HashMap<String, String>,
    labels: &std::collections::HashMap<String, String>,
) -> Option<IntegrityViolation> {
    // Constraint-Aware Auditing
    if kind == "Deployment" || kind == "StatefulSet" || kind == "DaemonSet" {
        for (k, v) in selector {
            if labels.get(k) != Some(v) {
                return Some(IntegrityViolation {
                    check_name: "SELECTOR-MISMATCH".to_string(),
                    severity: "HIGH".to_string(),
                    message: format!("Semantic Error: Selector key '{}={}' does not match pod template labels. This will cause deployment failure.", k, v),
                    rule_id: "REL-000".to_string(),
                    line_no: 0,
                });
            }
        }
    }
    None
}

pub fn audit_indentation_grid(indent: usize, dominant_step: usize) -> Option<IntegrityViolation> {
    // Indentation Consistency Auditing
    if dominant_step > 0 && indent % dominant_step != 0 {
        Some(IntegrityViolation {
            check_name: "INDENTATION-GRID-MISMATCH".to_string(),
            severity: "INFO".to_string(),
            message: format!("Style Error: Indentation of {} spaces is not a multiple of the dominant grid step ({}). Maintain consistent indentation for production readability.", indent, dominant_step),
            rule_id: "BST-000".to_string(),
            line_no: 0,
        })
    } else {
        None
    }
}

pub fn audit_secret_leakage(kind: &str, value: &str) -> Option<IntegrityViolation> {
    // SealedSecrets are encrypted with cluster public keys and safe for git repositories
    if kind == "SealedSecret" {
        return None;
    }

    let secret_patterns = [
        "BEGIN RSA PRIVATE KEY",
        "BEGIN OPENSSH PRIVATE KEY",
        "BEGIN PRIVATE KEY",
        "AWS_SECRET_ACCESS_KEY",
        "export STRIPE_API_KEY",
        "client_secret:",
    ];

    for pattern in secret_patterns {
        if value.contains(pattern) {
            let message = if kind == "Secret" {
                "Security Critical: Cleartext private key or credential directly embedded in Secret manifest. Manifests should use SealedSecrets, SOPS, or ExternalSecrets in version control.".to_string()
            } else {
                format!("Security Critical: Potential secret leakage detected in Kind '{}'. Sensitive data should be stored in an encrypted Secret resource.", kind)
            };
            return Some(IntegrityViolation {
                check_name: "SECRET-LEAKAGE-DETECTED".to_string(),
                severity: "CRITICAL".to_string(),
                message,
                rule_id: "SEC-006".to_string(),
                line_no: 0,
            });
        }
    }

    // Heuristic: High-entropy long strings without spaces in env vars or config data
    // In Secret manifests, base64 values under data are expected, but in plain non-Secret resources it indicates a leak.
    if kind != "Secret"
        && value.len() > 64
        && !value.contains(' ')
        && (value
            .chars()
            .all(|c| c.is_alphanumeric() || c == '+' || c == '/' || c == '='))
    {
        return Some(IntegrityViolation {
                check_name: "HIGH-ENTROPY-VALUE".to_string(),
                severity: "HIGH".to_string(),
                message: format!("Security Warning: High-entropy value detected in Kind '{}'. Verify that this is not a leaked credential.", kind),
                rule_id: "SEC-006".to_string(),
                line_no: 0,
            });
    }

    None
}

pub fn audit_data_key(kind: &str, key: &str) -> Option<IntegrityViolation> {
    // Key-Safe Auditing
    if kind == "ConfigMap" || kind == "Secret" {
        // K8s Keys must match [-._a-zA-Z0-9]+
        let is_valid = key
            .chars()
            .all(|c| c.is_alphanumeric() || c == '-' || c == '.' || c == '_');
        if !is_valid {
            return Some(IntegrityViolation {
                check_name: "INVALID-DATA-KEY".to_string(),
                severity: "HIGH".to_string(),
                rule_id: "MET-004".to_string(),
                message: format!("Semantic Error: Key '{}' in Kind '{}' contains invalid characters. Keys must only contain alphanumeric characters, '-', '.', or '_'.", key, kind),
                line_no: 0,
            });
        }
    }
    None
}

pub fn audit_label_key(key: &str) -> Option<IntegrityViolation> {
    // Label-Safe Auditing
    // Simple check: labels must not contain spaces or certain special chars
    // Valid chars: alphanumeric, '-', '.', '_', and one '/' for prefix
    let mut slash_count = 0;
    let is_valid = key.chars().all(|c| {
        if c == '/' {
            slash_count += 1;
            return true;
        }
        c.is_alphanumeric() || c == '-' || c == '.' || c == '_'
    });

    if !is_valid || slash_count > 1 {
        return Some(IntegrityViolation {
            check_name: "INVALID-LABEL-KEY".to_string(),
            severity: "HIGH".to_string(),
            rule_id: "MET-003".to_string(),
            message: format!("Semantic Error: Label key '{}' contains invalid characters. Kubernetes labels must follow DNS naming conventions.", key),
            line_no: 0,
        });
    }
    None
}

pub fn audit_annotation_key(key: &str) -> Option<IntegrityViolation> {
    // Annotation-Safe Auditing
    // Similar to labels, but often more permissive in value, key is still restricted
    let mut slash_count = 0;
    let is_valid = key.chars().all(|c| {
        if c == '/' {
            slash_count += 1;
            return true;
        }
        c.is_alphanumeric() || c == '-' || c == '.' || c == '_'
    });

    if !is_valid || slash_count > 1 {
        return Some(IntegrityViolation {
            check_name: "INVALID-ANNOTATION-KEY".to_string(),
            severity: "HIGH".to_string(),
            rule_id: "MET-005".to_string(),
            message: format!("Semantic Error: Annotation key '{}' contains invalid characters. Kubernetes annotations must follow DNS naming conventions.", key),
            line_no: 0,
        });
    }
    None
}

pub fn calculate_health_score(violations: &[IntegrityViolation]) -> f64 {
    // Deterministic Health Scoring
    // Standard: Base score of 100.0, penalized by violation severity.
    let mut score = 100.0;
    for v in violations {
        let penalty = match v.severity.as_str() {
            "CRITICAL" => 15.0,
            "HIGH" => 10.0,
            "WARNING" => 5.0,
            "INFO" => 1.0,
            _ => 2.0,
        };
        score -= penalty;
    }
    f64::max(score, 0.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audit_manifest_deprecation() {
        let result = audit_manifest("extensions/v1beta1", "Deployment");
        let _ = result;
    }

    #[test]
    fn test_audit_image_immutability() {
        let bad1 = audit_image("nginx:latest");
        assert!(bad1.is_some());
        assert_eq!(bad1.unwrap().rule_id, "OPS-002");

        let bad2 = audit_image("nginx");
        assert!(bad2.is_some());

        let good = audit_image("nginx:1.21.0");
        assert!(good.is_none());
    }

    #[test]
    fn test_audit_resource_ratio() {
        let burst_oom = audit_resource_ratio("4000m", "256Mi");
        assert!(burst_oom.is_some());
        assert_eq!(burst_oom.unwrap().rule_id, "REL-010");

        let safe = audit_resource_ratio("1000m", "1024Mi");
        assert!(safe.is_none());
    }

    #[test]
    fn test_audit_flow_style() {
        let flow = audit_flow_style("selector");
        assert!(flow.is_some());
        assert_eq!(flow.unwrap().rule_id, "BST-000");
    }

    #[test]
    fn test_audit_secret_leakage() {
        let leak = audit_secret_leakage("Deployment", "BEGIN RSA PRIVATE KEY");
        assert!(leak.is_some());
        assert_eq!(leak.unwrap().rule_id, "SEC-006");

        let entropy = audit_secret_leakage(
            "ConfigMap",
            "zxcasdqwe123zxcasdqwe123zxcasdqwe123zxcasdqwe123zxcasdqwe123zxcasdqw",
        );
        assert!(entropy.is_some());

        // Embedded cleartext private key in Secret is now flagged as CRITICAL
        let secret = audit_secret_leakage("Secret", "BEGIN RSA PRIVATE KEY");
        assert!(secret.is_some());
        assert_eq!(secret.unwrap().severity, "CRITICAL");

        // SealedSecret is properly encrypted
        let sealed = audit_secret_leakage("SealedSecret", "BEGIN RSA PRIVATE KEY");
        assert!(sealed.is_none());
    }

    #[test]
    fn test_calculate_health_score() {
        // Need to guess the exact fields for IntegrityViolation based on how audit_engine instantiates it.
        // It has check_name, message, severity, rule_id, line_no. Let's provide them.
        let v1 = IntegrityViolation {
            check_name: "c1".into(),
            message: "m1".into(),
            severity: "CRITICAL".into(),
            rule_id: "1".into(),
            line_no: 0,
        };
        let v2 = IntegrityViolation {
            check_name: "c2".into(),
            message: "m2".into(),
            severity: "HIGH".into(),
            rule_id: "2".into(),
            line_no: 0,
        };
        let violations = vec![v1, v2];
        let score = calculate_health_score(&violations);
        assert_eq!(score, 75.0);
    }
}
