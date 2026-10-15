//! Quoted Integer & Numeric Field Normalizer (Rule TYP-002).
//!
//! Why: In Helm charts and templated manifests, numbers are frequently quoted by template
//! engines: e.g. `containerPort: "8080"`, `replicas: "3"`, or `terminationGracePeriodSeconds: "30"`.
//! The `kube-apiserver` strictly expects an `integer` (int32) according to the OpenAPI schema.
//! Unstripped quotes cause admission validation rejections (`Invalid value: "string": expected integer`).
//!
//! This module identifies known integer fields in the Kubernetes schema and strips quotes
//! when the value parses unambiguously into an integer, while preserving named ports like `targetPort: "http"`.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_TYP_002: &str = "TYP-002";

/// Fields that Kubernetes OpenAPI schema strictly requires as integer scalars.
pub static STRICT_INTEGER_FIELDS: &[&str] = &[
    "containerPort",
    "hostPort",
    "port",
    "replicas",
    "terminationGracePeriodSeconds",
    "initialDelaySeconds",
    "timeoutSeconds",
    "periodSeconds",
    "successThreshold",
    "failureThreshold",
    "activeDeadlineSeconds",
    "backoffLimit",
    "minReadySeconds",
    "progressDeadlineSeconds",
    "revisionHistoryLimit",
];

/// Strips enclosing single or double quotes from a string if it parses as an integer.
pub fn normalize_quoted_integer(val: &str) -> Option<String> {
    let trimmed = val.trim();
    if (trimmed.starts_with('"') && trimmed.ends_with('"') && trimmed.len() >= 2)
        || (trimmed.starts_with('\'') && trimmed.ends_with('\'') && trimmed.len() >= 2)
    {
        let inner = &trimmed[1..trimmed.len() - 1];
        if inner.parse::<i64>().is_ok() {
            return Some(inner.to_string());
        }
    }
    None
}

/// Recursively traverses the SemanticNode tree and unquotes strict integer fields.
pub fn normalize_integers_in_node(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if STRICT_INTEGER_FIELDS.contains(&node.key.as_str()) {
        if let Some(val) = &node.value {
            if let Some(unquoted) = normalize_quoted_integer(val) {
                let msg = format!(
                    "Remediation [{}]: Normalized quoted integer for key '{}' from {} to {}.",
                    RULE_TYP_002, node.key, val, unquoted
                );
                node.value = Some(unquoted.clone());
                for s in &mut node.shards {
                    s.value = Some(unquoted.clone());
                }
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    // Special case for targetPort: can be integer or string (name).
    // If it's a quoted integer like "8080", normalize it to 8080.
    if node.key == "targetPort" {
        if let Some(val) = &node.value {
            if let Some(unquoted) = normalize_quoted_integer(val) {
                let msg = format!(
                    "Remediation [{}]: Normalized quoted integer for key 'targetPort' from {} to {}.",
                    RULE_TYP_002, val, unquoted
                );
                node.value = Some(unquoted.clone());
                for s in &mut node.shards {
                    s.value = Some(unquoted.clone());
                }
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    // Trap 30: Illegal Octal Digits in unquoted numbers (e.g. `08` or `09`)
    // Leading zero makes YAML treat as octal, but 8 and 9 are invalid octal digits, causing fatal parser errors.
    // Wrap them in quotes to preserve user's intended string/revision tag.
    if let Some(ref val) = node.value {
        let trimmed = val.trim();
        if !trimmed.starts_with('"') && !trimmed.starts_with('\'') && trimmed.starts_with('0') && trimmed.len() >= 2 {
            if trimmed.chars().all(|c| c.is_ascii_digit()) && (trimmed.contains('8') || trimmed.contains('9')) {
                let quoted = format!("\"{}\"", trimmed);
                let msg = format!(
                    "Remediation [TYP-005]: Quoted illegal octal literal '{}' -> '{}' to prevent YAML parser crashes.",
                    trimmed, quoted
                );
                node.value = Some(quoted.clone());
                for s in &mut node.shards {
                    s.value = Some(quoted.clone());
                }
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    for child in &mut node.children {
        normalize_integers_in_node(child, telemetry, changes);
    }
}

/// Primary Entrypoint: Strips quotes on strict integer fields across all Kubernetes resources.
pub fn heal_quoted_integers(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    normalize_integers_in_node(&mut manifest.root, telemetry, &mut changes);
    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_quoted_integer() {
        assert_eq!(normalize_quoted_integer("\"8080\""), Some("8080".to_string()));
        assert_eq!(normalize_quoted_integer("'3'"), Some("3".to_string()));
        assert_eq!(normalize_quoted_integer("\"30\""), Some("30".to_string()));

        // Named ports or non-integers should be unchanged
        assert_eq!(normalize_quoted_integer("\"http\""), None);
        assert_eq!(normalize_quoted_integer("'metrics'"), None);
        assert_eq!(normalize_quoted_integer("8080"), None);
    }

    #[test]
    fn test_illegal_octals_quoted() {
        let mut node = SemanticNode {
            key: "revision".to_string(),
            value: Some("08".to_string()), // Trap 30: unquoted 08
            indent: 2,
            is_empty_flow: false,
            shards: Vec::new(),
            children: Vec::new(),
        };

        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();
        normalize_integers_in_node(&mut node, &mut telemetry, &mut changes);

        assert_eq!(changes.len(), 1);
        assert_eq!(node.value, Some("\"08\"".to_string()));
    }
}
