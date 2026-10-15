//! Kubernetes Beta Topology and Failure-Domain Key Modernizer (Rule TOPO-001 / Trap 54).
//!
//! Why: In Kubernetes 1.17+, legacy beta labels and topology keys were deprecated and replaced by GA equivalents:
//! - `failure-domain.beta.kubernetes.io/zone` -> `topology.kubernetes.io/zone`
//! - `failure-domain.beta.kubernetes.io/region` -> `topology.kubernetes.io/region`
//! - `beta.kubernetes.io/os` -> `kubernetes.io/os`
//! - `beta.kubernetes.io/arch` -> `kubernetes.io/arch`
//!
//! In modern Kubernetes clusters (K8s 1.24+ on EKS, AKS, GKE, and kubeadm), worker nodes no longer publish
//! the legacy `beta.kubernetes.io` labels. Workloads specifying these deprecated keys in `nodeSelector`,
//! `topologySpreadConstraints[].topologyKey`, or `nodeAffinity...matchExpressions[].key` remain permanently
//! stuck in `Pending` state (`0/N nodes available: node(s) didn't match Pod's node affinity/selector`).
//!
//! This healer automatically and deterministically modernizes legacy beta topology keys across all workload
//! selectors and constraints while preserving comments and values.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_TOPO_001: &str = "TOPO-001";

/// Mapping of deprecated beta failure-domain and topology keys to GA equivalents.
pub static LEGACY_TOPOLOGY_KEYS: &[(&str, &str)] = &[
    (
        "failure-domain.beta.kubernetes.io/zone",
        "topology.kubernetes.io/zone",
    ),
    (
        "failure-domain.beta.kubernetes.io/region",
        "topology.kubernetes.io/region",
    ),
    ("beta.kubernetes.io/os", "kubernetes.io/os"),
    ("beta.kubernetes.io/arch", "kubernetes.io/arch"),
];

/// Recursively traverses Pod specs to modernize legacy topology and failure-domain labels.
fn modernize_topology_keys_recursive(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    // 1. nodeSelector mapping keys: `failure-domain.beta.kubernetes.io/zone: us-east-1a`
    if node.key == "nodeSelector" {
        for child in &mut node.children {
            for &(legacy, modern) in LEGACY_TOPOLOGY_KEYS {
                if child.key == legacy {
                    let old_key = child.key.clone();
                    child.key = modern.to_string();
                    for s in &mut child.shards {
                        s.key = modern.to_string();
                    }
                    let msg = format!(
                        "Remediation [{}]: Modernized legacy topology label in nodeSelector '{}' -> '{}'.",
                        RULE_TOPO_001, old_key, modern
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    // 2. topologySpreadConstraints[].topologyKey: `topologyKey: failure-domain.beta.kubernetes.io/zone`
    if node.key == "topologyKey" {
        let val_clone = node.value.clone();
        if let Some(val) = val_clone {
            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
            for &(legacy, modern) in LEGACY_TOPOLOGY_KEYS {
                if clean == legacy {
                    let old_val = val.clone();
                    let canonical = format!("\"{}\"", modern);
                    node.value = Some(canonical.clone());
                    for s in &mut node.shards {
                        s.value = Some(canonical.clone());
                    }
                    let msg = format!(
                        "Remediation [{}]: Modernized legacy topologyKey '{}' -> '{}'.",
                        RULE_TOPO_001, old_val, canonical
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    // 3. nodeAffinity matchExpressions[].key: `key: failure-domain.beta.kubernetes.io/zone`
    if node.key == "key" {
        let val_clone = node.value.clone();
        if let Some(val) = val_clone {
            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
            for &(legacy, modern) in LEGACY_TOPOLOGY_KEYS {
                if clean == legacy {
                    let old_val = val.clone();
                    let is_quoted = val.trim().starts_with('"') || val.trim().starts_with('\'');
                    let canonical = if is_quoted {
                        format!("\"{}\"", modern)
                    } else {
                        modern.to_string()
                    };
                    node.value = Some(canonical.clone());
                    for s in &mut node.shards {
                        s.value = Some(canonical.clone());
                    }
                    let msg = format!(
                        "Remediation [{}]: Modernized legacy topology matchExpression key '{}' -> '{}'.",
                        RULE_TOPO_001, old_val, canonical
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    for child in &mut node.children {
        modernize_topology_keys_recursive(child, telemetry, changes);
    }
}

/// Primary Entrypoint: Modernizes legacy topology keys in manifests.
pub fn heal_topology_keys(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    modernize_topology_keys_recursive(&mut manifest.root, telemetry, &mut changes);
    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_modernize_node_selector_and_topology_key() {
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
                                                        key: "failure-domain.beta.kubernetes.io/zone".to_string(),
                                                        value: Some("us-east-1a".to_string()),
                                                        indent: 8,
                                                        is_empty_flow: false,
                                                        children: Vec::new(),
                                                        shards: Vec::new(),
                                                    },
                                                    SemanticNode {
                                                        key: "beta.kubernetes.io/os".to_string(),
                                                        value: Some("linux".to_string()),
                                                        indent: 8,
                                                        is_empty_flow: false,
                                                        children: Vec::new(),
                                                        shards: Vec::new(),
                                                    },
                                                ],
                                            },
                                            SemanticNode {
                                                key: "topologySpreadConstraints".to_string(),
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
                                                                key: "topologyKey".to_string(),
                                                                value: Some("\"failure-domain.beta.kubernetes.io/region\"".to_string()),
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

        let changes = heal_topology_keys(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 3);
        assert!(changes[0].contains("[TOPO-001]"));

        let spec = manifest.root.find_node("spec").unwrap();
        let tmpl = spec.find_node("template").unwrap();
        let pod_spec = tmpl.find_node("spec").unwrap();
        let ns = pod_spec.find_node("nodeSelector").unwrap();

        assert_eq!(ns.find_value("topology.kubernetes.io/zone"), Some("us-east-1a".to_string()));
        assert_eq!(ns.find_value("kubernetes.io/os"), Some("linux".to_string()));
        assert!(ns.find_node("failure-domain.beta.kubernetes.io/zone").is_none());

        let tsc = pod_spec.find_node("topologySpreadConstraints").unwrap();
        let item = &tsc.children[0];
        assert_eq!(item.find_value("topologyKey"), Some("\"topology.kubernetes.io/region\"".to_string()));
    }
}
