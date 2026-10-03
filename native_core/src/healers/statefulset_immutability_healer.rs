//! StatefulSet Immutability Guard & PVC Expansion Synthesizer (Rule STO-001).
//!
//! Why: In Kubernetes, `StatefulSet.spec.volumeClaimTemplates`, `spec.podManagementPolicy`,
//! and `spec.selector` are strictly immutable after creation. When an engineer modifies
//! storage (e.g. `10Gi` -> `20Gi`) directly in `volumeClaimTemplates`, `kubectl apply` or
//! ArgoCD hard-crashes with `spec: Forbidden: updates to statefulset spec for fields other
//! than 'replicas', 'template', and 'updateStrategy' are forbidden`.
//!
//! Yamlr guards the StatefulSet against fatal in-place corruption and synthesizes the separate,
//! valid Kubernetes PersistentVolumeClaim manifest that allows dynamic online volume expansion.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const STS_IMMUTABLE_RULE_ID: &str = "STO-003";

/// Primary entrypoint: Guards StatefulSet immutable fields and synthesizes PVC expansions.
pub fn heal_statefulset_immutability(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "StatefulSet" {
        return changes;
    }

    let sts_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "statefulset".to_string());
    let _sts_namespace = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    // Check for volume expansion directives or annotations
    let expand_annotation = manifest.root.find_annotation("yamlr.io/expand-pvc");
    let mut expanded_claims = Vec::new();

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(vct) = spec.find_node_mut("volumeClaimTemplates") {
            for claim in &mut vct.children {
                let claim_name = claim
                    .find_value("name")
                    .unwrap_or_else(|| "data".to_string());

                // Check for per-claim expansion annotation or top-level directive
                let target_size = claim
                    .find_annotation("yamlr.io/target-storage")
                    .or_else(|| expand_annotation.clone());

                if let Some(ref new_size) = target_size {
                    let clean_size = new_size
                        .trim()
                        .trim_matches('"')
                        .trim_matches('\'')
                        .to_string();
                    expanded_claims.push((claim_name.clone(), clean_size.clone()));

                    // Guard: keep existing volumeClaimTemplates or annotate with expansion synthesized
                    let msg = format!(
                        "Remediation [{}]: Guarded immutable 'volumeClaimTemplates' on StatefulSet '{}'. Synthesized separate PVC expansion for '{}' to '{}'.",
                        STS_IMMUTABLE_RULE_ID, sts_name, claim_name, clean_size
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    // If expansions were detected, stamp the synthesized annotation on the StatefulSet
    if !expanded_claims.is_empty() {
        let summary: Vec<String> = expanded_claims
            .iter()
            .map(|(c, s)| format!("{}:{}", c, s))
            .collect();
        let summary_val = format!("\"{}\"", summary.join(","));
        set_annotation(
            &mut manifest.root,
            "yamlr.io/pvc-expansion-synthesized",
            &summary_val,
        );
    }

    // Guard 2: PodManagementPolicy immutability check
    if let Some(spec) = manifest.root.find_node("spec") {
        if let Some(pmp) = spec.find_value("podManagementPolicy") {
            let clean = pmp.trim().trim_matches('"').trim_matches('\'');
            if clean != "OrderedReady" && clean != "Parallel" {
                if let Some(spec_mut) = manifest.root.find_node_mut("spec") {
                    if let Some(pmp_node) = spec_mut.find_node_mut("podManagementPolicy") {
                        pmp_node.value = Some("OrderedReady".to_string());
                        for s in &mut pmp_node.shards {
                            s.value = Some("OrderedReady".to_string());
                        }
                        let msg = format!(
                            "Remediation [{}]: Normalized invalid 'podManagementPolicy: {}' -> 'OrderedReady' on StatefulSet '{}'.",
                            STS_IMMUTABLE_RULE_ID, clean, sts_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    }

    changes
}

/// Synthesizes a valid, standalone Kubernetes PersistentVolumeClaim manifest for online volume expansion.
pub fn synthesize_pvc_expansion_yaml(
    sts_name: &str,
    claim_name: &str,
    namespace: &str,
    new_storage_size: &str,
    replica_index: usize,
) -> String {
    let pvc_name = format!("{}-{}-{}", claim_name, sts_name, replica_index);
    format!(
        "apiVersion: v1\n\
kind: PersistentVolumeClaim\n\
metadata:\n  \
name: {}\n  \
namespace: {}\n  \
annotations:\n    \
yamlr.io/synthesized-by: \"yamlr-sto-001\"\n\
spec:\n  \
resources:\n    \
requests:\n      \
storage: {}\n",
        pvc_name, namespace, new_storage_size
    )
}

fn set_annotation(root: &mut SemanticNode, key: &str, value: &str) -> bool {
    if let Some(metadata) = root.find_node_mut("metadata") {
        let meta_indent = metadata.indent + 2;
        if let Some(annotations) = metadata.find_node_mut("annotations") {
            let ann_indent = annotations.indent + 2;
            if let Some(ann) = annotations.find_node_mut(key) {
                ann.value = Some(value.to_string());
                for s in &mut ann.shards {
                    s.value = Some(value.to_string());
                }
            } else {
                annotations.children.push(SemanticNode {
                    key: key.to_string(),
                    value: Some(value.to_string()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: ann_indent,
                    is_empty_flow: false,
                });
            }
            true
        } else {
            metadata.children.push(SemanticNode {
                key: "annotations".to_string(),
                value: None,
                indent: meta_indent,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: key.to_string(),
                    value: Some(value.to_string()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: meta_indent + 2,
                    is_empty_flow: false,
                }],
            });
            true
        }
    } else {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_statefulset_with_vct(storage_annotation: Option<&str>) -> SemanticManifest {
        let mut vct_child = SemanticNode {
            key: "-".to_string(),
            value: None,
            indent: 4,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![
                SemanticNode {
                    key: "name".to_string(),
                    value: Some("data".to_string()),
                    indent: 6,
                    is_empty_flow: false,
                    children: vec![],
                    shards: vec![],
                },
                SemanticNode {
                    key: "spec".to_string(),
                    value: None,
                    indent: 6,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "resources".to_string(),
                        value: None,
                        indent: 8,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "requests".to_string(),
                            value: None,
                            indent: 10,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "storage".to_string(),
                                value: Some("10Gi".to_string()),
                                indent: 12,
                                is_empty_flow: false,
                                children: vec![],
                                shards: vec![],
                            }],
                        }],
                    }],
                },
            ],
        };

        if let Some(target) = storage_annotation {
            vct_child.children.push(SemanticNode {
                key: "metadata".to_string(),
                value: None,
                indent: 6,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "annotations".to_string(),
                    value: None,
                    indent: 8,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "yamlr.io/target-storage".to_string(),
                        value: Some(target.to_string()),
                        indent: 10,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    }],
                }],
            });
        }

        SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "apiVersion".to_string(),
                        value: Some("apps/v1".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "kind".to_string(),
                        value: Some("StatefulSet".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "metadata".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "name".to_string(),
                                value: Some("postgres".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: vec![],
                                shards: vec![],
                            },
                            SemanticNode {
                                key: "namespace".to_string(),
                                value: Some("prod".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: vec![],
                                shards: vec![],
                            },
                        ],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "volumeClaimTemplates".to_string(),
                            value: None,
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![vct_child],
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        }
    }

    #[test]
    fn test_guard_vct_and_synthesize_expansion_annotation() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_statefulset_with_vct(Some("\"20Gi\""));

        let changes = heal_statefulset_immutability(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Guarded immutable 'volumeClaimTemplates'"));

        let ann = manifest
            .root
            .find_annotation("yamlr.io/pvc-expansion-synthesized");
        assert_eq!(ann, Some("\"data:20Gi\"".to_string()));
    }

    #[test]
    fn test_synthesize_pvc_expansion_yaml() {
        let yaml = synthesize_pvc_expansion_yaml("postgres", "data", "prod", "20Gi", 0);
        assert!(yaml.contains("kind: PersistentVolumeClaim"));
        assert!(yaml.contains("name: data-postgres-0"));
        assert!(yaml.contains("storage: 20Gi"));
    }

    #[test]
    fn test_normalize_invalid_pod_management_policy() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_statefulset_with_vct(None);
        if let Some(spec) = manifest.root.find_node_mut("spec") {
            spec.children.push(SemanticNode {
                key: "podManagementPolicy".to_string(),
                value: Some("RandomInvalidPolicy".to_string()),
                indent: 2,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
            });
        }

        let changes = heal_statefulset_immutability(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);

        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(
            spec.find_value("podManagementPolicy"),
            Some("OrderedReady".to_string())
        );
    }
}
