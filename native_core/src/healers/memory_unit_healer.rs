//! Memory Unit & Millibyte Sanitizer (Rule RES-004).
//!
//! Why: In Kubernetes manifests, memory quantity formatting errors cause severe runtime failures:
//! 1. Millibytes error: Writing `memory: 500m` parses as 500 millibytes (0.5 bytes). Kubelet
//!    immediately OOMKills the container on creation (exit code 137), causing instant CrashLoopBackOff.
//! 2. Suffix casing/format errors: Writing `500mb`, `500MB`, `1gb`, `1GB` is rejected by
//!    `kube-apiserver` admission validation (`quantities must match the regular expression...`).
//! 3. Standard decimal values like `200M` and `500G` are preserved as valid SI notation.
//!
//! This module heals accidental millibytes (`500m` -> `500Mi`) and invalid suffixes (`500mb` -> `500Mi`).

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_RES_004: &str = "RES-004";

/// Sanitizes an invalid or dangerous memory string into official Kubernetes binary notation (Mi/Gi/Ki).
/// Preserves legitimate decimal notation (`200M`, `500G`, `100k`) as-is.
pub fn sanitize_memory_quantity(raw_val: &str) -> Option<String> {
    let trimmed = raw_val.trim().trim_matches(|c| c == '\'' || c == '"');
    if trimmed.is_empty() {
        return None;
    }

    // 1. Catastrophic Millibyte Bug: e.g. "500m", "250m" (lowercase m on memory)
    // In K8s quantities, lowercase 'm' is milli (10^-3). On memory, this is 0.5 bytes!
    if trimmed.ends_with('m') && !trimmed.ends_with("Mi") && !trimmed.ends_with("mi") {
        let num_part = &trimmed[..trimmed.len() - 1];
        if num_part.parse::<f64>().is_ok() {
            return Some(format!("{}Mi", num_part));
        }
    }

    // 2. Invalid casing / unofficial suffixes: "mb", "MB", "Mb", "mB"
    let lower = trimmed.to_ascii_lowercase();
    if lower.ends_with("mb") {
        let num_part = &trimmed[..trimmed.len() - 2];
        if num_part.parse::<f64>().is_ok() {
            return Some(format!("{}Mi", num_part));
        }
    }

    // 3. Invalid "gb", "GB", "Gb"
    if lower.ends_with("gb") {
        let num_part = &trimmed[..trimmed.len() - 2];
        if num_part.parse::<f64>().is_ok() {
            return Some(format!("{}Gi", num_part));
        }
    }

    // 4. Invalid "kb", "KB", "Kb"
    if lower.ends_with("kb") {
        let num_part = &trimmed[..trimmed.len() - 2];
        if num_part.parse::<f64>().is_ok() {
            return Some(format!("{}Ki", num_part));
        }
    }

    // 5. Lowercase single-char units for large scales: e.g. "1g" -> "1Gi"
    if trimmed.ends_with('g') {
        let num_part = &trimmed[..trimmed.len() - 1];
        if num_part.parse::<f64>().is_ok() {
            return Some(format!("{}Gi", num_part));
        }
    }

    // 6. Trap 60 / Rule RES-006: Suffix casing errors (e.g. "500mi", "500MI", "1gi", "1GI", "256ki", "256KI", "1ti", "1TI")
    // Official Kubernetes binary units must be strictly "Ki", "Mi", "Gi", "Ti", "Pi", "Ei".
    for (bad_suffix, correct_suffix) in [
        ("mi", "Mi"),
        ("MI", "Mi"),
        ("gi", "Gi"),
        ("GI", "Gi"),
        ("ki", "Ki"),
        ("KI", "Ki"),
        ("ti", "Ti"),
        ("TI", "Ti"),
        ("pi", "Pi"),
        ("PI", "Pi"),
    ] {
        if trimmed.ends_with(bad_suffix) && !trimmed.ends_with(correct_suffix) {
            let num_part = &trimmed[..trimmed.len() - bad_suffix.len()];
            if num_part.parse::<f64>().is_ok() {
                return Some(format!("{}{}", num_part, correct_suffix));
            }
        }
    }

    None
}

/// Recursively inspects memory nodes under requests and limits and corrects invalid units.
pub fn heal_memory_units_in_node(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "memory" {
        if let Some(val) = &node.value {
            if let Some(repaired) = sanitize_memory_quantity(val) {
                let msg = format!(
                    "Remediation [{}]: Sanitized fatal memory unit '{}' to '{}'.",
                    RULE_RES_004, val, repaired
                );
                node.value = Some(repaired.clone());
                for s in &mut node.shards {
                    s.value = Some(repaired.clone());
                }
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    for child in &mut node.children {
        heal_memory_units_in_node(child, telemetry, changes);
    }
}

/// Primary Entrypoint: Sanitizes fatal millibytes and invalid memory suffixes across all containers.
pub fn heal_memory_units(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    for c_node in manifest.root.find_nodes_by_key_recursive_mut("containers") {
        for container in &mut c_node.children {
            if let Some(resources_node) = container.find_node_mut("resources") {
                heal_memory_units_in_node(resources_node, telemetry, &mut changes);
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize_memory_quantity() {
        // Catastrophic millibyte bug
        assert_eq!(sanitize_memory_quantity("500m"), Some("500Mi".to_string()));
        assert_eq!(sanitize_memory_quantity("256m"), Some("256Mi".to_string()));

        // Invalid suffixes
        assert_eq!(sanitize_memory_quantity("500mb"), Some("500Mi".to_string()));
        assert_eq!(sanitize_memory_quantity("500MB"), Some("500Mi".to_string()));
        assert_eq!(sanitize_memory_quantity("2gb"), Some("2Gi".to_string()));
        assert_eq!(sanitize_memory_quantity("1g"), Some("1Gi".to_string()));

        // Legitimate standard notation preserved as-is
        assert_eq!(sanitize_memory_quantity("500Mi"), None);
        assert_eq!(sanitize_memory_quantity("2Gi"), None);
        assert_eq!(sanitize_memory_quantity("200M"), None);
        assert_eq!(sanitize_memory_quantity("500G"), None);
    }
}
