//! NodeSelector Mapping Normalizer & Sequence Flattener (Rule TYP-004 / Trap 51).
//!
//! Why: In Kubernetes Pod specifications (`spec.nodeSelector`), `nodeSelector` is strictly defined as
//! a map of string keys to string values (`map[string]string`). Authors frequently confuse `nodeSelector`
//! with `matchExpressions` or list syntax and declare it as a sequence:
//!
//! ```yaml
//! nodeSelector:
//!   - disktype: ssd
//!   - region: us-west-2
//! ```
//!
//! The Kubernetes `kube-apiserver` admission controller immediately rejects this manifest with:
//! `spec.template.spec.nodeSelector: Invalid value: "array": expected map`.
//!
//! This healer flattens accidentally sequenced list items under `nodeSelector` back into
//! a standard key-value map while strictly preserving comments and indentation.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_TYP_004: &str = "TYP-004";

/// Recursively scans for Pod specs and normalizes sequence-formatted `nodeSelector` blocks into maps.
fn heal_node_selector_recursive(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "nodeSelector" {
        // Check if nodeSelector has children that are sequence items (e.g. key == "-" or is_list_item)
        let is_sequence = node.children.iter().any(|c| {
            c.key == "-" || c.shards.first().map_or(false, |s| s.is_list_item)
        });

        if is_sequence && !node.children.is_empty() {
            let mut flattened_children = Vec::new();
            let parent_indent = node.indent;

            for list_item in &mut node.children {
                if list_item.key == "-" {
                    for mut grand_child in list_item.children.drain(..) {
                        grand_child.indent = parent_indent + 2;
                        // Strip list bullet flags from shards if present
                        for shard in &mut grand_child.shards {
                            shard.is_list_item = false;
                        }
                        flattened_children.push(grand_child);
                    }
                } else {
                    let mut child = list_item.clone();
                    child.indent = parent_indent + 2;
                    for shard in &mut child.shards {
                        shard.is_list_item = false;
                    }
                    flattened_children.push(child);
                }
            }

            if !flattened_children.is_empty() {
                node.children = flattened_children;
                let msg = format!(
                    "Remediation [{}]: Converted sequence under 'nodeSelector' into valid key-value map.",
                    RULE_TYP_004
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    for child in &mut node.children {
        heal_node_selector_recursive(child, telemetry, changes);
    }
}

/// Primary Entrypoint: Resolves sequence-to-map syntax errors under `nodeSelector`.
pub fn heal_node_selector_syntax(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    heal_node_selector_recursive(&mut manifest.root, telemetry, &mut changes);
    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heal_node_selector_sequence_to_map() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".to_string(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "kind".to_string(),
                        value: Some("Deployment".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "template".to_string(),
                                value: None,
                                indent: 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![
                                    SemanticNode {
                                        key: "spec".to_string(),
                                        value: None,
                                        indent: 4,
                                        is_empty_flow: false,
                                        shards: Vec::new(),
                                        children: vec![
                                            SemanticNode {
                                                key: "nodeSelector".to_string(),
                                                value: None,
                                                indent: 6,
                                                is_empty_flow: false,
                                                shards: Vec::new(),
                                                children: vec![
                                                    SemanticNode {
                                                        key: "-".to_string(),
                                                        value: None,
                                                        indent: 8,
                                                        is_empty_flow: false,
                                                        shards: Vec::new(),
                                                        children: vec![
                                                            SemanticNode {
                                                                key: "disktype".to_string(),
                                                                value: Some("ssd".to_string()),
                                                                indent: 10,
                                                                is_empty_flow: false,
                                                                children: Vec::new(),
                                                                shards: Vec::new(),
                                                            },
                                                        ],
                                                    },
                                                    SemanticNode {
                                                        key: "-".to_string(),
                                                        value: None,
                                                        indent: 8,
                                                        is_empty_flow: false,
                                                        shards: Vec::new(),
                                                        children: vec![
                                                            SemanticNode {
                                                                key: "kubernetes.io/os".to_string(),
                                                                value: Some("linux".to_string()),
                                                                indent: 10,
                                                                is_empty_flow: false,
                                                                children: Vec::new(),
                                                                shards: Vec::new(),
                                                            },
                                                        ],
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_node_selector_syntax(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("[TYP-004]"));

        let spec = manifest.root.find_node("spec").unwrap();
        let tmpl = spec.find_node("template").unwrap();
        let pod_spec = tmpl.find_node("spec").unwrap();
        let ns = pod_spec.find_node("nodeSelector").unwrap();

        assert_eq!(ns.children.len(), 2);
        assert_eq!(ns.find_value("disktype"), Some("ssd".to_string()));
        assert_eq!(ns.find_value("kubernetes.io/os"), Some("linux".to_string()));
        assert!(ns.find_node("-").is_none());
    }
}
