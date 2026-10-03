//! Enum Value Typo Correction and Normalization Engine (Feature 2 of 15).
//!
//! Why: Kubernetes OpenAPI definitions require strict case-sensitive enum values
//! (e.g. `imagePullPolicy: Always`, not `Alway` or `always`; `type: ClusterIP`,
//! not `clusterip` or `LoadBalncr`). Misspelled or incorrectly-cased enums cause
//! silent deployment failures or immediate rejection by kube-apiserver.
//!
//! This module provides deterministic case normalization and Levenshtein fuzzy
//! matching for all standard Kubernetes enumerated fields.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub static IMAGE_PULL_POLICY_ENUM: &[&str] = &["Always", "IfNotPresent", "Never"];
pub static RESTART_POLICY_ENUM: &[&str] = &["Always", "OnFailure", "Never"];
pub static SERVICE_TYPE_ENUM: &[&str] = &["ClusterIP", "NodePort", "LoadBalancer", "ExternalName"];
pub static DNS_POLICY_ENUM: &[&str] =
    &["ClusterFirst", "Default", "ClusterFirstWithHostNet", "None"];
pub static SESSION_AFFINITY_ENUM: &[&str] = &["None", "ClientIP"];
pub static PROTOCOL_ENUM: &[&str] = &["TCP", "UDP", "SCTP"];
pub static PATH_TYPE_ENUM: &[&str] = &["Prefix", "Exact", "ImplementationSpecific"];
pub static TERMINATION_MESSAGE_POLICY_ENUM: &[&str] = &["File", "FallbackToLogsOnError"];
pub static CONCURRENCY_POLICY_ENUM: &[&str] = &["Allow", "Forbid", "Replace"];
pub static ACCESS_MODES_ENUM: &[&str] = &[
    "ReadWriteOnce",
    "ReadOnlyMany",
    "ReadWriteMany",
    "ReadWriteOncePod",
];
pub static RECLAIM_POLICY_ENUM: &[&str] = &["Retain", "Recycle", "Delete"];
pub static VOLUME_MODE_ENUM: &[&str] = &["Filesystem", "Block"];
pub static IP_FAMILY_POLICY_ENUM: &[&str] = &["SingleStack", "PreferDualStack", "RequireDualStack"];
pub static EXTERNAL_TRAFFIC_POLICY_ENUM: &[&str] = &["Cluster", "Local"];
pub static POD_MANAGEMENT_POLICY_ENUM: &[&str] = &["OrderedReady", "Parallel"];

pub static BOOLEAN_KEYS: &[&str] = &[
    "hostNetwork",
    "hostPID",
    "hostIPC",
    "automountServiceAccountToken",
    "readOnly",
    "privileged",
    "allowPrivilegeEscalation",
    "runAsNonRoot",
    "stdin",
    "tty",
];

/// Match an input enum string against expected candidates.
/// Returns Some(&'static str) if a case correction or typo fix is found.
pub fn fuzzy_match_enum(input_val: &str, candidates: &[&'static str]) -> Option<&'static str> {
    let cleaned = input_val
        .trim()
        .trim_matches(|c| c == '\'' || c == '"')
        .trim();
    if cleaned.is_empty() {
        return None;
    }

    // 1. Exact match (already correct)
    if candidates.contains(&cleaned) {
        return None;
    }

    // 2. Case-insensitive exact match (e.g. "clusterip" -> "ClusterIP")
    for &cand in candidates {
        if cand.eq_ignore_ascii_case(cleaned) {
            return Some(cand);
        }
    }

    // 3. Fuzzy matching using Levenshtein distance
    if cleaned.len() >= 3 {
        let input_lower = cleaned.to_lowercase();
        let mut best_cand = None;
        let mut min_dist = usize::MAX;

        for &cand in candidates {
            let cand_lower = cand.to_lowercase();
            let dist = crate::healers::typo_healer::levenshtein(&input_lower, &cand_lower);

            let max_allowed_dist = if cleaned.len() <= 5 { 1 } else { 2 };

            if dist <= max_allowed_dist && dist < min_dist {
                let max_len = cleaned.len().max(cand.len());
                let ratio = (max_len - dist) as f64 / max_len as f64;
                if ratio >= 0.65 {
                    min_dist = dist;
                    best_cand = Some(cand);
                }
            }
        }
        return best_cand;
    }

    None
}

/// Coerces boolean strings (e.g. "yes", "on", "True", "'true'") to normalized "true" or "false".
pub fn coerce_boolean_value(input_val: &str) -> Option<&'static str> {
    let cleaned = input_val
        .trim()
        .trim_matches(|c| c == '\'' || c == '"')
        .trim();
    let lower = cleaned.to_lowercase();
    if lower == "true" || lower == "yes" || lower == "on" {
        if input_val != "true" {
            return Some("true");
        }
    } else if lower == "false" || lower == "no" || lower == "off" {
        if input_val != "false" {
            return Some("false");
        }
    }
    None
}

/// Recursively traverses AST to detect and heal enum typos and type mismatches.
fn heal_enum_node_recursive(
    node: &mut SemanticNode,
    parent_key: &str,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    for child in &mut node.children {
        // Boolean Coercion Check
        if BOOLEAN_KEYS.contains(&child.key.as_str()) {
            if let Some(ref val) = child.value {
                if let Some(coerced) = coerce_boolean_value(val) {
                    let old_val = val.clone();
                    child.value = Some(coerced.to_string());
                    for shard in &mut child.shards {
                        shard.value = Some(coerced.to_string());
                    }
                    let msg = format!(
                        "Remediation [SCHEMA-003]: Coerced boolean value for '{}': '{}' -> '{}'.",
                        child.key, old_val, coerced
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }

        // Enum Typo & Case Correction Check
        let candidates: Option<&[&str]> = match child.key.as_str() {
            "imagePullPolicy" => Some(IMAGE_PULL_POLICY_ENUM),
            "restartPolicy" => Some(RESTART_POLICY_ENUM),
            "type" => {
                if let Some(ref val) = child.value {
                    let v_clean = val
                        .trim()
                        .trim_matches(|c| c == '\'' || c == '"')
                        .to_lowercase();
                    if SERVICE_TYPE_ENUM.iter().any(|&e| {
                        e.to_lowercase() == v_clean
                            || crate::healers::typo_healer::levenshtein(&e.to_lowercase(), &v_clean)
                                <= 2
                    }) {
                        Some(SERVICE_TYPE_ENUM)
                    } else {
                        None
                    }
                } else {
                    None
                }
            }
            "dnsPolicy" => Some(DNS_POLICY_ENUM),
            "sessionAffinity" => Some(SESSION_AFFINITY_ENUM),
            "protocol" => Some(PROTOCOL_ENUM),
            "pathType" => Some(PATH_TYPE_ENUM),
            "terminationMessagePolicy" => Some(TERMINATION_MESSAGE_POLICY_ENUM),
            "concurrencyPolicy" => Some(CONCURRENCY_POLICY_ENUM),
            "reclaimPolicy" | "persistentVolumeReclaimPolicy" => Some(RECLAIM_POLICY_ENUM),
            "volumeMode" => Some(VOLUME_MODE_ENUM),
            "ipFamilyPolicy" => Some(IP_FAMILY_POLICY_ENUM),
            "externalTrafficPolicy" => Some(EXTERNAL_TRAFFIC_POLICY_ENUM),
            "podManagementPolicy" => Some(POD_MANAGEMENT_POLICY_ENUM),
            "-" => {
                if parent_key == "accessModes" {
                    Some(ACCESS_MODES_ENUM)
                } else {
                    None
                }
            }
            _ => None,
        };

        if let Some(cand_list) = candidates {
            if let Some(ref val) = child.value {
                if let Some(corrected) = fuzzy_match_enum(val, cand_list) {
                    let old_val = val.clone();
                    child.value = Some(corrected.to_string());
                    for shard in &mut child.shards {
                        shard.value = Some(corrected.to_string());
                    }
                    let key_display = if child.key == "-" {
                        format!("{}[*]", parent_key)
                    } else {
                        child.key.clone()
                    };
                    let msg = format!(
                        "Remediation [SCHEMA-003]: Coerced enum value for '{}': '{}' -> '{}'.",
                        key_display, old_val, corrected
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }

        let current_key = child.key.clone();
        heal_enum_node_recursive(child, &current_key, telemetry, changes);
    }
}

/// Primary Entrypoint: Heals all enum typos and casing mismatches across a manifest.
pub fn heal_enum_typos(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let root_key = manifest.root.key.clone();
    heal_enum_node_recursive(&mut manifest.root, &root_key, telemetry, &mut changes);
    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fuzzy_match_image_pull_policy() {
        assert_eq!(
            fuzzy_match_enum("Alway", IMAGE_PULL_POLICY_ENUM),
            Some("Always")
        );
        assert_eq!(
            fuzzy_match_enum("always", IMAGE_PULL_POLICY_ENUM),
            Some("Always")
        );
        assert_eq!(
            fuzzy_match_enum("ifnotpresent", IMAGE_PULL_POLICY_ENUM),
            Some("IfNotPresent")
        );
        assert_eq!(
            fuzzy_match_enum("IfNotPresent", IMAGE_PULL_POLICY_ENUM),
            None
        );
        assert_eq!(
            fuzzy_match_enum("Neverr", IMAGE_PULL_POLICY_ENUM),
            Some("Never")
        );
    }

    #[test]
    fn test_fuzzy_match_service_type() {
        assert_eq!(
            fuzzy_match_enum("clusterip", SERVICE_TYPE_ENUM),
            Some("ClusterIP")
        );
        assert_eq!(
            fuzzy_match_enum("nodeport", SERVICE_TYPE_ENUM),
            Some("NodePort")
        );
        assert_eq!(
            fuzzy_match_enum("LoadBalncr", SERVICE_TYPE_ENUM),
            Some("LoadBalancer")
        );
        assert_eq!(fuzzy_match_enum("LoadBalancer", SERVICE_TYPE_ENUM), None);
    }

    #[test]
    fn test_coerce_boolean() {
        assert_eq!(coerce_boolean_value("yes"), Some("true"));
        assert_eq!(coerce_boolean_value("no"), Some("false"));
        assert_eq!(coerce_boolean_value("\"true\""), Some("true"));
        assert_eq!(coerce_boolean_value("true"), None);
    }
}
