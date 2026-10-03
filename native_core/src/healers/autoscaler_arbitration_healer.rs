//! Autoscaler Metric Contention Healer: HPA vs VPA Conflict Arbitrator (Rule AUT-002).
//!
//! Why: When a HorizontalPodAutoscaler (HPA) and a VerticalPodAutoscaler (VPA) simultaneously
//! manage the same target workload on identical metrics (CPU or Memory), the two controllers
//! fight in an infinite feedback loop:
//! 1. High traffic load triggers HPA horizontal scale-out.
//! 2. VPA simultaneously increases CPU/Memory resource requests per pod.
//! 3. The combined scaling over-provisions the workload, triggering simultaneous scale-in
//!    and down-sizing.
//! 4. This cycle causes frequent pod evictions, OOMKilled crashes, and cluster thrashing.
//!
//! Yamlr cross-resource graph inspects HPAs and VPAs targeting the same workload and arbitrates:
//! - In VPA: Adjusts `updateMode` or restricts `controlledResources` to prevent collision.
//! - In HPA: Emits clear, explainable remediation guidance.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const AUTOSCALER_CONCURRENT_RULE_ID: &str = "AUT-002";

/// Arbitrates autoscaler contention between HPA and VPA targeting the same workload.
pub fn heal_autoscaler_arbitration(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    if kind != "VerticalPodAutoscaler"
        && kind != "VPA"
        && kind != "HorizontalPodAutoscaler"
        && kind != "HPA"
    {
        return changes;
    }

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let target_workload = manifest
        .root
        .find_node("spec")
        .and_then(|s| {
            s.find_node("scaleTargetRef")
                .or_else(|| s.find_node("targetRef"))
        })
        .and_then(|tr| tr.find_value("name"))
        .map(|n| n.trim().trim_matches('"').trim_matches('\'').to_string());

    let Some(workload_name) = target_workload else {
        return changes;
    };

    if workload_name.is_empty() {
        return changes;
    }

    if kind == "VerticalPodAutoscaler" || kind == "VPA" {
        // Check if an HPA targets the exact same workload in the same namespace
        let matching_hpa = identities.iter().find(|id| {
            (id.kind == "HorizontalPodAutoscaler" || id.kind == "HPA")
                && (id.namespace == ns || id.namespace.is_empty() || id.namespace == "default")
                && id.service_refs.contains(&workload_name)
        });

        if let Some(hpa_id) = matching_hpa {
            if let Some(spec) = manifest.root.find_node_mut("spec") {
                // Check current VPA updateMode
                let update_policy = spec.find_node_mut("updatePolicy");
                let mut current_mode = "Auto".to_string();

                if let Some(ref up) = update_policy {
                    if let Some(m) = up.find_value("updateMode") {
                        current_mode = m.trim().trim_matches('"').trim_matches('\'').to_string();
                    }
                }

                // If VPA is actively mutating pods ("Auto" or "Recreate"):
                // Check if resourcePolicy is present to restrict controlledResources to ["memory"],
                // otherwise switch updateMode to "Off".
                if current_mode == "Auto" || current_mode == "Recreate" {
                    let indent = spec.indent + 2;

                    // Option A: If resourcePolicy exists, restrict containerPolicies controlledResources: ["memory"]
                    if let Some(res_policy) = spec.find_node_mut("resourcePolicy") {
                        let pol_indent = res_policy.indent + 2;
                        let target_cp = match res_policy.find_node_mut("containerPolicies") {
                            Some(cp) => cp,
                            None => {
                                res_policy.children.push(SemanticNode {
                                    key: "containerPolicies".to_string(),
                                    value: None,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                    indent: pol_indent,
                                    is_empty_flow: false,
                                });
                                res_policy.children.last_mut().unwrap()
                            }
                        };

                        let cp_item_indent = target_cp.indent + 2;
                        let item = SemanticNode {
                            key: "-".to_string(),
                            value: None,
                            children: vec![
                                SemanticNode {
                                    key: "containerName".to_string(),
                                    value: Some("\"*\"".to_string()),
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                    indent: cp_item_indent + 2,
                                    is_empty_flow: false,
                                },
                                SemanticNode {
                                    key: "controlledResources".to_string(),
                                    value: None,
                                    children: vec![SemanticNode {
                                        key: "-".to_string(),
                                        value: Some("\"memory\"".to_string()),
                                        children: Vec::new(),
                                        shards: Vec::new(),
                                        indent: cp_item_indent + 4,
                                        is_empty_flow: false,
                                    }],
                                    shards: Vec::new(),
                                    indent: cp_item_indent + 2,
                                    is_empty_flow: false,
                                },
                            ],
                            shards: Vec::new(),
                            indent: cp_item_indent,
                            is_empty_flow: false,
                        };
                        target_cp.children.push(item);

                        let msg = format!(
                            "Remediation [{}]: Mitigated autoscaler conflict: Restricted VPA controlledResources to ['memory'] to prevent CPU scaling war with HPA '{}' on '{}'.",
                            AUTOSCALER_CONCURRENT_RULE_ID, hpa_id.name, workload_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    } else {
                        // Option B: Shift updateMode to "Off" (recommendation-only mode)
                        let target_node = match spec.find_node_mut("updatePolicy") {
                            Some(up) => up,
                            None => {
                                spec.children.push(SemanticNode {
                                    key: "updatePolicy".to_string(),
                                    value: None,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                    indent,
                                    is_empty_flow: false,
                                });
                                spec.children.last_mut().unwrap()
                            }
                        };

                        let up_indent = target_node.indent + 2;
                        if let Some(mode_node) = target_node.find_node_mut("updateMode") {
                            mode_node.value = Some("\"Off\"".to_string());
                            for s in &mut mode_node.shards {
                                s.value = Some("\"Off\"".to_string());
                            }
                        } else {
                            target_node.children.push(SemanticNode {
                                key: "updateMode".to_string(),
                                value: Some("\"Off\"".to_string()),
                                children: Vec::new(),
                                shards: Vec::new(),
                                indent: up_indent,
                                is_empty_flow: false,
                            });
                        }

                        let msg = format!(
                            "Remediation [{}]: Mitigated autoscaler conflict: Shifted VPA updateMode 'Auto' -> 'Off' because HPA '{}' is actively scaling workload '{}'.",
                            AUTOSCALER_CONCURRENT_RULE_ID, hpa_id.name, workload_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    } else if kind == "HorizontalPodAutoscaler" || kind == "HPA" {
        // In HPA manifest, detect if a VPA exists for the same target
        let matching_vpa = identities.iter().find(|id| {
            (id.kind == "VerticalPodAutoscaler" || id.kind == "VPA")
                && (id.namespace == ns || id.namespace.is_empty() || id.namespace == "default")
                && id.service_refs.contains(&workload_name)
        });

        if let Some(vpa_id) = matching_vpa {
            let msg = format!(
                "Advisory [{}]: Workload '{}' is concurrently targeted by HPA and VPA '{}'. Ensure HPA targets external/custom metrics or VPA controlledResources excludes CPU.",
                AUTOSCALER_CONCURRENT_RULE_ID, workload_name, vpa_id.name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::SemanticNode;

    #[test]
    fn test_arbitrate_hpa_vpa_contention() {
        let mut vpa_manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("VerticalPodAutoscaler".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "name".into(),
                                value: Some("orders-vpa".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "namespace".into(),
                                value: Some("prod".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                        ],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "targetRef".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "name".into(),
                                    value: Some("orders-api".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                }],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "updatePolicy".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "updateMode".into(),
                                    value: Some("\"Auto\"".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                }],
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

        let hpa_identity = NativeIdentity {
            kind: "HorizontalPodAutoscaler".into(),
            name: "orders-hpa".into(),
            namespace: "prod".into(),
            service_refs: vec!["orders-api".into()],
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes =
            heal_autoscaler_arbitration(&mut vpa_manifest, &[hpa_identity], &mut telemetry);
        assert_eq!(changes.len(), 1);

        let spec = vpa_manifest.root.find_node("spec").unwrap();
        let update_policy = spec.find_node("updatePolicy").unwrap();
        assert_eq!(
            update_policy.find_value("updateMode"),
            Some("\"Off\"".to_string())
        );
    }

    #[test]
    fn test_no_arbitration_when_target_differs() {
        let mut vpa_manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("VerticalPodAutoscaler".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "targetRef".into(),
                            value: None,
                            children: vec![SemanticNode {
                                key: "name".into(),
                                value: Some("cart-api".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            }],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        }],
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

        let hpa_identity = NativeIdentity {
            kind: "HorizontalPodAutoscaler".into(),
            name: "orders-hpa".into(),
            namespace: "default".into(),
            service_refs: vec!["orders-api".into()],
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes =
            heal_autoscaler_arbitration(&mut vpa_manifest, &[hpa_identity], &mut telemetry);
        assert_eq!(changes.len(), 0);
    }

    #[test]
    fn test_restrict_controlled_resources_when_resource_policy_present() {
        let mut vpa_manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("VerticalPodAutoscaler".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "name".into(),
                            value: Some("orders-vpa".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "targetRef".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "name".into(),
                                    value: Some("orders-api".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                }],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "resourcePolicy".into(),
                                value: None,
                                children: vec![],
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

        let hpa_identity = NativeIdentity {
            kind: "HorizontalPodAutoscaler".into(),
            name: "orders-hpa".into(),
            namespace: "default".into(),
            service_refs: vec!["orders-api".into()],
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes =
            heal_autoscaler_arbitration(&mut vpa_manifest, &[hpa_identity], &mut telemetry);
        assert_eq!(changes.len(), 1);

        let spec = vpa_manifest.root.find_node("spec").unwrap();
        let res_policy = spec.find_node("resourcePolicy").unwrap();
        let cp = res_policy.find_node("containerPolicies").unwrap();
        assert!(!cp.children.is_empty());
    }
}
