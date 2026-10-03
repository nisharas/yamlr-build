//! High Availability (HA) Topology Spread Synthesizer (Rule REL-011).
//!
//! Why: When developers set `replicas: 3` on a mission-critical workload without configuring
//! `topologySpreadConstraints` or `podAntiAffinity`, Kubernetes frequently schedules all replicas
//! onto the exact same worker node or single AWS/GCP/Azure Availability Zone (because that node
//! had the most free memory). A routine node reboot or AZ network blip causes a total service outage.
//!
//! Yamlr detects multi-replica workloads lacking spread rules and auto-injects production-grade
//! `topologySpreadConstraints` with `whenUnsatisfiable: ScheduleAnyway` to guarantee multi-zone
//! distribution without ever blocking scheduling in single-zone dev environments.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const HA_TOPOLOGY_RULE_ID: &str = "REL-011";

/// Primary entrypoint: Synthesizes topologySpreadConstraints for multi-replica workloads.
pub fn heal_topology_spread(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Deployment" && kind != "StatefulSet" && kind != "ReplicaSet" {
        return changes;
    }

    let workload_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "workload".to_string());

    // 1. Check replica count (> 1)
    let replica_count = manifest
        .root
        .find_node("spec")
        .and_then(|s| s.find_value("replicas"))
        .and_then(|r| {
            r.trim()
                .trim_matches('"')
                .trim_matches('\'')
                .parse::<usize>()
                .ok()
        })
        .unwrap_or(1);

    if replica_count <= 1 {
        return changes; // Single-replica workloads do not trigger topology spread injection
    }

    // 2. Extract matchLabels from selector
    let mut selector_labels: Vec<(String, String)> = Vec::new();
    if let Some(spec) = manifest.root.find_node("spec") {
        if let Some(sel) = spec.find_node("selector") {
            if let Some(ml) = sel.find_node("matchLabels") {
                for child in &ml.children {
                    if let Some(ref v) = child.value {
                        selector_labels.push((child.key.clone(), v.clone()));
                    }
                }
            }
        }
    }

    if selector_labels.is_empty() {
        // Fallback to app: <workload-name>
        selector_labels.push(("app".to_string(), workload_name.clone()));
    }

    // 3. Inspect pod template spec
    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(template) = spec.find_node_mut("template") {
            if let Some(pod_spec) = template.find_node_mut("spec") {
                // Check if topologySpreadConstraints already defined
                if let Some(tsc_node) = pod_spec.find_node_mut("topologySpreadConstraints") {
                    for item in &mut tsc_node.children {
                        // 1. maxSkew must be > 0 (if <= 0 or empty, heal to 1)
                        let mut needs_skew = false;
                        if let Some(skew_node) = item.find_node_mut("maxSkew") {
                            if let Some(ref val) = skew_node.value {
                                let parsed = val
                                    .trim()
                                    .trim_matches(|c| c == '\'' || c == '"')
                                    .parse::<i32>()
                                    .unwrap_or(0);
                                if parsed <= 0 {
                                    needs_skew = true;
                                }
                            } else {
                                needs_skew = true;
                            }
                            if needs_skew {
                                skew_node.value = Some("1".to_string());
                                for s in &mut skew_node.shards {
                                    s.value = Some("1".to_string());
                                }
                                let msg = format!(
                                    "Remediation [{}]: Fixed invalid 'maxSkew <= 0' -> '1' on topologySpreadConstraint.",
                                    HA_TOPOLOGY_RULE_ID
                                );
                                native_record_healing_impact(telemetry, &msg);
                                changes.push(msg);
                            }
                        }

                        // 2. whenUnsatisfiable validation (must be DoNotSchedule or ScheduleAnyway)
                        let mut needs_when = false;
                        let mut old_when = String::new();
                        if let Some(when_node) = item.find_node_mut("whenUnsatisfiable") {
                            if let Some(ref val) = when_node.value {
                                let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                                if clean != "DoNotSchedule" && clean != "ScheduleAnyway" {
                                    needs_when = true;
                                    old_when = clean.to_string();
                                }
                            } else {
                                needs_when = true;
                            }
                            if needs_when {
                                let healed = if old_when.to_lowercase().contains("donot")
                                    || (old_when.to_lowercase().contains("schedule")
                                        && old_when.to_lowercase().contains("not"))
                                {
                                    "DoNotSchedule".to_string()
                                } else {
                                    "ScheduleAnyway".to_string()
                                };
                                when_node.value = Some(healed.clone());
                                for s in &mut when_node.shards {
                                    s.value = Some(healed.clone());
                                }
                                let msg = format!(
                                    "Remediation [{}]: Normalized invalid whenUnsatisfiable '{}' -> '{}' on topologySpreadConstraint.",
                                    HA_TOPOLOGY_RULE_ID, old_when, healed
                                );
                                native_record_healing_impact(telemetry, &msg);
                                changes.push(msg);
                            }
                        }

                        // 3. topologyKey validation (must not be empty)
                        let mut needs_key = false;
                        if let Some(key_node) = item.find_node_mut("topologyKey") {
                            if let Some(ref val) = key_node.value {
                                if val
                                    .trim()
                                    .trim_matches(|c| c == '\'' || c == '"')
                                    .is_empty()
                                {
                                    needs_key = true;
                                }
                            } else {
                                needs_key = true;
                            }
                            if needs_key {
                                let default_key = "topology.kubernetes.io/zone".to_string();
                                key_node.value = Some(default_key.clone());
                                for s in &mut key_node.shards {
                                    s.value = Some(default_key.clone());
                                }
                                let msg = format!(
                                    "Remediation [{}]: Injected default topologyKey 'topology.kubernetes.io/zone' for empty key.",
                                    HA_TOPOLOGY_RULE_ID
                                );
                                native_record_healing_impact(telemetry, &msg);
                                changes.push(msg);
                            }
                        }
                    }
                    return changes; // Already had constraints (and any existing items were sanitized)
                }

                // Check if podAntiAffinity already defined
                if let Some(aff) = pod_spec.find_node("affinity") {
                    if aff.find_node("podAntiAffinity").is_some() {
                        return changes; // Pod anti-affinity satisfies HA spread requirement
                    }
                }

                // Inject topologySpreadConstraints
                let pod_spec_indent = pod_spec.indent + 2;
                let list_item_indent = pod_spec_indent + 2;
                let field_indent = list_item_indent + 2;
                let sel_indent = field_indent + 2;
                let ml_indent = sel_indent + 2;

                let match_label_nodes: Vec<SemanticNode> = selector_labels
                    .iter()
                    .map(|(k, v)| SemanticNode {
                        key: k.clone(),
                        value: Some(v.clone()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent: ml_indent + 2,
                        is_empty_flow: false,
                    })
                    .collect();

                let spread_constraint_item = SemanticNode {
                    key: "-".to_string(),
                    value: None,
                    indent: list_item_indent,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![
                        SemanticNode {
                            key: "maxSkew".to_string(),
                            value: Some("1".to_string()),
                            indent: field_indent,
                            is_empty_flow: false,
                            children: vec![],
                            shards: vec![],
                        },
                        SemanticNode {
                            key: "topologyKey".to_string(),
                            value: Some("topology.kubernetes.io/zone".to_string()),
                            indent: field_indent,
                            is_empty_flow: false,
                            children: vec![],
                            shards: vec![],
                        },
                        SemanticNode {
                            key: "whenUnsatisfiable".to_string(),
                            value: Some("ScheduleAnyway".to_string()),
                            indent: field_indent,
                            is_empty_flow: false,
                            children: vec![],
                            shards: vec![],
                        },
                        SemanticNode {
                            key: "labelSelector".to_string(),
                            value: None,
                            indent: field_indent,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "matchLabels".to_string(),
                                value: None,
                                indent: sel_indent,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: match_label_nodes,
                            }],
                        },
                    ],
                };

                pod_spec.children.push(SemanticNode {
                    key: "topologySpreadConstraints".to_string(),
                    value: None,
                    indent: pod_spec_indent,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![spread_constraint_item],
                });

                let msg = format!(
                    "Remediation [{}]: Injected HA 'topologySpreadConstraints' (topologyKey: topology.kubernetes.io/zone, maxSkew: 1, ScheduleAnyway) on {} '{}' with {} replicas.",
                    HA_TOPOLOGY_RULE_ID, kind, workload_name, replica_count
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_deployment(
        replicas: usize,
        with_spread: bool,
        with_anti_affinity: bool,
    ) -> SemanticManifest {
        let mut pod_spec_children = vec![SemanticNode {
            key: "containers".to_string(),
            value: None,
            indent: 8,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "-".to_string(),
                value: None,
                indent: 10,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "name".to_string(),
                    value: Some("web".to_string()),
                    indent: 12,
                    is_empty_flow: false,
                    children: vec![],
                    shards: vec![],
                }],
            }],
        }];

        if with_spread {
            pod_spec_children.push(SemanticNode {
                key: "topologySpreadConstraints".to_string(),
                value: None,
                indent: 8,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
            });
        }

        if with_anti_affinity {
            pod_spec_children.push(SemanticNode {
                key: "affinity".to_string(),
                value: None,
                indent: 8,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "podAntiAffinity".to_string(),
                    value: None,
                    indent: 10,
                    is_empty_flow: false,
                    children: vec![],
                    shards: vec![],
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
                        value: Some("Deployment".to_string()),
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
                        children: vec![SemanticNode {
                            key: "name".to_string(),
                            value: Some("checkout-service".to_string()),
                            indent: 2,
                            is_empty_flow: false,
                            children: vec![],
                            shards: vec![],
                        }],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "replicas".to_string(),
                                value: Some(replicas.to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: vec![],
                                shards: vec![],
                            },
                            SemanticNode {
                                key: "selector".to_string(),
                                value: None,
                                indent: 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "matchLabels".to_string(),
                                    value: None,
                                    indent: 4,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "app".to_string(),
                                        value: Some("checkout".to_string()),
                                        indent: 6,
                                        is_empty_flow: false,
                                        children: vec![],
                                        shards: vec![],
                                    }],
                                }],
                            },
                            SemanticNode {
                                key: "template".to_string(),
                                value: None,
                                indent: 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "spec".to_string(),
                                    value: None,
                                    indent: 6,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: pod_spec_children,
                                }],
                            },
                        ],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        }
    }

    #[test]
    fn test_inject_spread_constraints_for_replicas_3() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_deployment(3, false, false);

        let changes = heal_topology_spread(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Injected HA 'topologySpreadConstraints'"));

        let spec = manifest.root.find_node("spec").unwrap();
        let tmpl = spec.find_node("template").unwrap();
        let pod_spec = tmpl.find_node("spec").unwrap();
        let tsc = pod_spec.find_node("topologySpreadConstraints").unwrap();
        assert_eq!(tsc.children.len(), 1);
        let first_constraint = &tsc.children[0];
        assert_eq!(
            first_constraint.find_value("maxSkew"),
            Some("1".to_string())
        );
        assert_eq!(
            first_constraint.find_value("topologyKey"),
            Some("topology.kubernetes.io/zone".to_string())
        );
        assert_eq!(
            first_constraint.find_value("whenUnsatisfiable"),
            Some("ScheduleAnyway".to_string())
        );
    }

    #[test]
    fn test_skip_single_replica() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_deployment(1, false, false);

        let changes = heal_topology_spread(&mut manifest, &mut telemetry);
        assert!(changes.is_empty());
    }

    #[test]
    fn test_skip_when_already_has_spread_constraints() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_deployment(3, true, false);

        let changes = heal_topology_spread(&mut manifest, &mut telemetry);
        assert!(changes.is_empty());
    }

    #[test]
    fn test_skip_when_already_has_anti_affinity() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_deployment(3, false, true);

        let changes = heal_topology_spread(&mut manifest, &mut telemetry);
        assert!(changes.is_empty());
    }

    #[test]
    fn test_heal_existing_invalid_topology_spread_constraint() {
        let mut telemetry = NativeTelemetry::default();
        let yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-workload
spec:
  replicas: 3
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 0
          topologyKey: ""
          whenUnsatisfiable: Schedule
"#;
        let mut manifest =
            crate::structurer::native_structurize(crate::sharder::native_shard(yaml));
        let changes = heal_topology_spread(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 3);
        assert!(changes
            .iter()
            .any(|c| c.contains("Fixed invalid 'maxSkew <= 0' -> '1'")));
        assert!(changes
            .iter()
            .any(|c| c
                .contains("Normalized invalid whenUnsatisfiable 'Schedule' -> 'ScheduleAnyway'")));
        assert!(changes
            .iter()
            .any(|c| c.contains("Injected default topologyKey 'topology.kubernetes.io/zone'")));
    }
}
