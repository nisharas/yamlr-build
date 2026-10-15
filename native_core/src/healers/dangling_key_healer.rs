//! Dangling Null-Sequence Pruner (Rule SYN-008).
//!
//! Why: When developers comment out all items under an array field (e.g. `env:`, `args:`, `command:`, `ports:`):
//! ```yaml
//! env:
//! # - name: DEBUG
//! #   value: "true"
//! ```
//! YAML parsers evaluate `env:` as `null` (`None`). When applied to Kubernetes apiserver,
//! the schema validator rejects the resource because array fields cannot be `null`.
//!
//! This module detects dangling array keys that contain no children and have no scalar value,
//! and either cleans them up or normalizes them into empty flow sequences `[]` without losing surrounding comments.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_SYN_008: &str = "SYN-008";

/// Known array fields that must not be null/empty in Kubernetes workload specifications.
pub static STRICT_ARRAY_FIELDS: &[&str] = &[
    "env",
    "args",
    "command",
    "ports",
    "volumeMounts",
    "volumes",
    "imagePullSecrets",
    "tolerations",
    "initContainers",
];

/// Prunes or normalizes dangling empty array fields.
pub fn prune_dangling_arrays(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let mut to_remove = Vec::new();

    for (idx, child) in node.children.iter_mut().enumerate() {
        if STRICT_ARRAY_FIELDS.contains(&child.key.as_str()) {
            // If child has no children and value is either None, "~", "null", or empty string
            let is_null_val = match &child.value {
                None => true,
                Some(v) => {
                    let t = v.trim();
                    t == "null" || t == "~" || t.is_empty()
                }
            };

            if is_null_val && child.children.is_empty() {
                to_remove.push(idx);
            }
        }
    }

    if !to_remove.is_empty() {
        for idx in to_remove.into_iter().rev() {
            let removed_key = node.children[idx].key.clone();
            node.children.remove(idx);
            let msg = format!(
                "Remediation [{}]: Pruned dangling null-sequence key '{}' left empty by commented items.",
                RULE_SYN_008, removed_key
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    for child in &mut node.children {
        prune_dangling_arrays(child, telemetry, changes);
    }
}

/// Primary Entrypoint: Prunes dangling null arrays across all Kubernetes resources.
pub fn heal_dangling_arrays(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    prune_dangling_arrays(&mut manifest.root, telemetry, &mut changes);
    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_prune_dangling_arrays() {
        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();

        let mut root = SemanticNode {
            key: "root".to_string(),
            value: None,
            indent: 0,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![
                SemanticNode {
                    key: "env".to_string(),
                    value: None,
                    indent: 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
                SemanticNode {
                    key: "image".to_string(),
                    value: Some("nginx".to_string()),
                    indent: 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
            ],
        };

        prune_dangling_arrays(&mut root, &mut telemetry, &mut changes);
        assert_eq!(changes.len(), 1);
        assert_eq!(root.children.len(), 1);
        assert_eq!(root.children[0].key, "image");
    }
}
