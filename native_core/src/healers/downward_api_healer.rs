//! Downward API fieldPath Syntax Healer (Rule DAPI-001 / Trap 44).
//!
//! Why: In Kubernetes Pod specs, the Downward API (`env[].valueFrom.fieldRef.fieldPath`)
//! allows containers to reflect metadata like labels and annotations.
//! The Kubernetes Downward API parser strictly requires subscript syntax (`metadata.labels['key']`
//! or `metadata.annotations['key']`).
//!
//! Developers commonly make syntax errors:
//! 1. Dot notation: `fieldPath: metadata.labels.app` or `metadata.annotations.app`
//! 2. Double-quoted subscript: `fieldPath: metadata.labels["app"]`
//! 3. Bare subscript: `fieldPath: metadata.labels[app]`
//!
//! These syntax errors cause kubelet to reject pod startup immediately:
//! `fieldPath "metadata.labels.app" is not supported: invalid fieldPath for Pod`.
//!
//! This module deterministically transforms malformed Downward API label and annotation
//! lookups into the canonical `metadata.labels['<key>']` format with zero guesswork.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_DAPI_001: &str = "DAPI-001";

/// Normalizes a raw fieldPath string into canonical Downward API subscript syntax.
pub fn normalize_downward_api_field_path(raw_path: &str) -> Option<String> {
    let clean = raw_path.trim().trim_matches(|c| c == '\'' || c == '"');

    for prefix in &["metadata.labels", "metadata.annotations"] {
        if clean.starts_with(prefix) && clean.len() > prefix.len() {
            let remainder = &clean[prefix.len()..];

            // 1. Dot notation: `metadata.labels.app` -> `metadata.labels['app']`
            if remainder.starts_with('.') {
                let key = &remainder[1..];
                if !key.is_empty() && !key.contains('[') && !key.contains('\'') {
                    return Some(format!("\"{}['{}']\"", prefix, key));
                }
            }

            // 2. Double-quoted subscript: `metadata.labels["app"]` -> `metadata.labels['app']`
            if remainder.starts_with("[\"") && remainder.ends_with("\"]") && remainder.len() > 4 {
                let key = &remainder[2..remainder.len() - 2];
                return Some(format!("\"{}['{}']\"", prefix, key));
            }

            // 3. Unquoted bracket subscript: `metadata.labels[app]` -> `metadata.labels['app']`
            if remainder.starts_with('[') && remainder.ends_with(']') && !remainder.contains('\'') && !remainder.contains('"') && remainder.len() > 2 {
                let key = &remainder[1..remainder.len() - 1];
                return Some(format!("\"{}['{}']\"", prefix, key));
            }
        }
    }

    None
}

/// Recursively scans and heals Downward API fieldPath references across containers.
pub fn heal_downward_api_field_paths(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    fn traverse_and_heal(
        node: &mut SemanticNode,
        telemetry: &mut NativeTelemetry,
        changes: &mut Vec<String>,
    ) {
        if node.key == "fieldPath" {
            if let Some(val) = &node.value {
                if let Some(healed) = normalize_downward_api_field_path(val) {
                    if healed != *val {
                        let old_val = val.clone();
                        node.value = Some(healed.clone());
                        for s in &mut node.shards {
                            s.value = Some(healed.clone());
                        }

                        let msg = format!(
                            "Remediation [{}]: Normalized Downward API fieldPath '{}' -> '{}' to prevent kubelet admission rejection.",
                            RULE_DAPI_001, old_val, healed
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }

        for child in &mut node.children {
            traverse_and_heal(child, telemetry, changes);
        }
    }

    traverse_and_heal(&mut manifest.root, telemetry, &mut changes);
    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_downward_api_field_path() {
        assert_eq!(
            normalize_downward_api_field_path("metadata.labels.app"),
            Some("\"metadata.labels['app']\"".to_string())
        );
        assert_eq!(
            normalize_downward_api_field_path("metadata.annotations.version"),
            Some("\"metadata.annotations['version']\"".to_string())
        );
        assert_eq!(
            normalize_downward_api_field_path("metadata.labels[\"app\"]"),
            Some("\"metadata.labels['app']\"".to_string())
        );
        assert_eq!(
            normalize_downward_api_field_path("metadata.labels[app]"),
            Some("\"metadata.labels['app']\"".to_string())
        );
        // Already valid should be None
        assert_eq!(normalize_downward_api_field_path("metadata.labels['app']"), None);
    }

    #[test]
    fn test_heal_downward_api_manifest() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Pod".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "containers".into(),
                                value: None,
                                children: vec![
                                    SemanticNode {
                                        key: "-".into(),
                                        value: None,
                                        children: vec![
                                            SemanticNode {
                                                key: "name".into(),
                                                value: Some("app".into()),
                                                children: vec![],
                                                shards: vec![],
                                                indent: 6,
                                                is_empty_flow: false,
                                            },
                                            SemanticNode {
                                                key: "env".into(),
                                                value: None,
                                                children: vec![
                                                    SemanticNode {
                                                        key: "-".into(),
                                                        value: None,
                                                        children: vec![
                                                            SemanticNode {
                                                                key: "name".into(),
                                                                value: Some("POD_LABEL".into()),
                                                                children: vec![],
                                                                shards: vec![],
                                                                indent: 10,
                                                                is_empty_flow: false,
                                                            },
                                                            SemanticNode {
                                                                key: "valueFrom".into(),
                                                                value: None,
                                                                children: vec![
                                                                    SemanticNode {
                                                                        key: "fieldRef".into(),
                                                                        value: None,
                                                                        children: vec![
                                                                            SemanticNode {
                                                                                key: "fieldPath".into(),
                                                                                value: Some("metadata.labels.app".into()),
                                                                                children: vec![],
                                                                                shards: vec![],
                                                                                indent: 14,
                                                                                is_empty_flow: false,
                                                                            },
                                                                        ],
                                                                        shards: vec![],
                                                                        indent: 12,
                                                                        is_empty_flow: false,
                                                                    },
                                                                ],
                                                                shards: vec![],
                                                                indent: 10,
                                                                is_empty_flow: false,
                                                            },
                                                        ],
                                                        shards: vec![],
                                                        indent: 8,
                                                        is_empty_flow: false,
                                                    },
                                                ],
                                                shards: vec![],
                                                indent: 6,
                                                is_empty_flow: false,
                                            },
                                        ],
                                        shards: vec![],
                                        indent: 4,
                                        is_empty_flow: false,
                                    },
                                ],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                        ],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                ],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            indent_step: 2,
            integrity_violations: vec![],
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_downward_api_field_paths(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);

        let spec = manifest.root.find_node("spec").unwrap();
        let containers = spec.find_node("containers").unwrap();
        let env = containers.children[0].find_node("env").unwrap();
        let vf = env.children[0].find_node("valueFrom").unwrap();
        let fr = vf.find_node("fieldRef").unwrap();
        assert_eq!(
            fr.find_value("fieldPath"),
            Some("\"metadata.labels['app']\"".to_string())
        );
    }
}
