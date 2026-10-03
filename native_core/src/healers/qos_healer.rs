//! QoS Class Alignment & Burstable Right-Sizer (Rule RES-003).
//!
//! Why: In Kubernetes, containers lacking `resources:` are assigned the `BestEffort` Quality
//! of Service (QoS) class. When worker nodes experience memory pressure, the Linux kernel
//! OOM-killer and Kubelet terminate BestEffort pods first—taking down critical microservices
//! before background batch jobs! Conversely, unconfigured limits allow rogue containers to starve
//! neighbor pods on the same node.
//!
//! Yamlr detects naked `BestEffort` containers and synthesizes production-proven `Burstable` QoS
//! resource floors (`requests: cpu 50m, memory 64Mi; limits: cpu 500m, memory 256Mi`), preventing
//! unfair evictions while safeguarding cluster cost efficiency.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const QOS_ALIGN_RULE_ID: &str = "RES-003";

/// Primary entrypoint: Elevates naked BestEffort containers to safe Burstable QoS.
pub fn heal_qos_alignment(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    for pod_spec in manifest.root.find_pod_specs_mut() {
        if let Some(containers) = pod_spec.find_node_mut("containers") {
            for container in &mut containers.children {
                let c_name = container
                    .find_value("name")
                    .unwrap_or_else(|| "container".to_string());
                let c_indent = container.indent;

                let mut has_requests = false;
                let mut has_limits = false;

                if let Some(res) = container.find_node("resources") {
                    if let Some(req) = res.find_node("requests") {
                        if !req.children.is_empty() {
                            has_requests = true;
                        }
                    }
                    if let Some(lim) = res.find_node("limits") {
                        if !lim.children.is_empty() {
                            has_limits = true;
                        }
                    }
                }

                // Case 1: Completely naked container (BestEffort QoS) -> inject Burstable floor
                if !has_requests && !has_limits {
                    let res_indent = c_indent + 2;
                    let section_indent = res_indent + 2;
                    let val_indent = section_indent + 2;

                    let requests_node = SemanticNode {
                        key: "requests".to_string(),
                        value: None,
                        indent: section_indent,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "cpu".to_string(),
                                value: Some("50m".to_string()),
                                indent: val_indent,
                                is_empty_flow: false,
                                children: vec![],
                                shards: vec![],
                            },
                            SemanticNode {
                                key: "memory".to_string(),
                                value: Some("64Mi".to_string()),
                                indent: val_indent,
                                is_empty_flow: false,
                                children: vec![],
                                shards: vec![],
                            },
                        ],
                    };

                    let limits_node = SemanticNode {
                        key: "limits".to_string(),
                        value: None,
                        indent: section_indent,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "cpu".to_string(),
                                value: Some("500m".to_string()),
                                indent: val_indent,
                                is_empty_flow: false,
                                children: vec![],
                                shards: vec![],
                            },
                            SemanticNode {
                                key: "memory".to_string(),
                                value: Some("256Mi".to_string()),
                                indent: val_indent,
                                is_empty_flow: false,
                                children: vec![],
                                shards: vec![],
                            },
                        ],
                    };

                    if let Some(res) = container.find_node_mut("resources") {
                        res.children.push(requests_node);
                        res.children.push(limits_node);
                    } else {
                        container.children.push(SemanticNode {
                            key: "resources".to_string(),
                            value: None,
                            indent: res_indent,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![requests_node, limits_node],
                        });
                    }

                    let msg = format!(
                        "Remediation [{}]: Elevated container '{}' from BestEffort to Burstable QoS (requests: cpu 50m, mem 64Mi; limits: cpu 500m, mem 256Mi) to prevent OOM eviction.",
                        QOS_ALIGN_RULE_ID, c_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
                // Case 2: Has requests but missing limits -> add safe boundary limits
                else if has_requests && !has_limits {
                    if let Some(res) = container.find_node_mut("resources") {
                        let section_indent = res.indent + 2;
                        let val_indent = section_indent + 2;

                        res.children.push(SemanticNode {
                            key: "limits".to_string(),
                            value: None,
                            indent: section_indent,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![
                                SemanticNode {
                                    key: "cpu".to_string(),
                                    value: Some("500m".to_string()),
                                    indent: val_indent,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                                SemanticNode {
                                    key: "memory".to_string(),
                                    value: Some("256Mi".to_string()),
                                    indent: val_indent,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                            ],
                        });

                        let msg = format!(
                            "Remediation [{}]: Added boundary limits (cpu: 500m, mem: 256Mi) to container '{}' to prevent node resource exhaustion.",
                            QOS_ALIGN_RULE_ID, c_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
                // Case 3: Has limits but missing requests -> add minimum guaranteed baseline requests
                else if !has_requests && has_limits {
                    if let Some(res) = container.find_node_mut("resources") {
                        let section_indent = res.indent + 2;
                        let val_indent = section_indent + 2;

                        res.children.push(SemanticNode {
                            key: "requests".to_string(),
                            value: None,
                            indent: section_indent,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![
                                SemanticNode {
                                    key: "cpu".to_string(),
                                    value: Some("50m".to_string()),
                                    indent: val_indent,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                                SemanticNode {
                                    key: "memory".to_string(),
                                    value: Some("64Mi".to_string()),
                                    indent: val_indent,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                            ],
                        });

                        let msg = format!(
                            "Remediation [{}]: Added floor requests (cpu: 50m, mem: 64Mi) to container '{}' to guarantee Burstable scheduling.",
                            QOS_ALIGN_RULE_ID, c_name
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

#[cfg(test)]
mod tests {
    use super::*;

    fn create_workload_with_resources(res_children: Vec<SemanticNode>) -> SemanticManifest {
        let mut c_children = vec![
            SemanticNode {
                key: "name".to_string(),
                value: Some("app".to_string()),
                indent: 8,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
            },
            SemanticNode {
                key: "image".to_string(),
                value: Some("nginx:1.25".to_string()),
                indent: 8,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
            },
        ];
        if !res_children.is_empty() {
            c_children.push(SemanticNode {
                key: "resources".to_string(),
                value: None,
                indent: 8,
                is_empty_flow: false,
                shards: Vec::new(),
                children: res_children,
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
                            value: Some("web-server".to_string()),
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
                        children: vec![SemanticNode {
                            key: "template".to_string(),
                            value: None,
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "spec".to_string(),
                                value: None,
                                indent: 4,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "containers".to_string(),
                                    value: None,
                                    indent: 6,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "-".to_string(),
                                        value: None,
                                        indent: 8,
                                        is_empty_flow: false,
                                        shards: Vec::new(),
                                        children: c_children,
                                    }],
                                }],
                            }],
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        }
    }

    #[test]
    fn test_elevate_naked_container_to_burstable() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_workload_with_resources(vec![]);

        let changes = heal_qos_alignment(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Elevated container 'app' from BestEffort to Burstable QoS"));

        let res = manifest.root.find_pod_specs()[0]
            .find_node("containers")
            .unwrap()
            .children[0]
            .find_node("resources")
            .unwrap();

        let req = res.find_node("requests").unwrap();
        assert_eq!(req.find_value("cpu"), Some("50m".to_string()));
        assert_eq!(req.find_value("memory"), Some("64Mi".to_string()));

        let lim = res.find_node("limits").unwrap();
        assert_eq!(lim.find_value("cpu"), Some("500m".to_string()));
        assert_eq!(lim.find_value("memory"), Some("256Mi".to_string()));
    }

    #[test]
    fn test_add_limits_when_only_requests_present() {
        let mut telemetry = NativeTelemetry::default();
        let requests_node = SemanticNode {
            key: "requests".to_string(),
            value: None,
            indent: 10,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "cpu".to_string(),
                value: Some("100m".to_string()),
                indent: 12,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
            }],
        };
        let mut manifest = create_workload_with_resources(vec![requests_node]);

        let changes = heal_qos_alignment(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Added boundary limits"));

        let res = manifest.root.find_pod_specs()[0]
            .find_node("containers")
            .unwrap()
            .children[0]
            .find_node("resources")
            .unwrap();
        assert!(res.find_node("limits").is_some());
    }

    #[test]
    fn test_skip_already_burstable_container() {
        let mut telemetry = NativeTelemetry::default();
        let requests_node = SemanticNode {
            key: "requests".to_string(),
            value: None,
            indent: 10,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "cpu".to_string(),
                value: Some("100m".to_string()),
                indent: 12,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
            }],
        };
        let limits_node = SemanticNode {
            key: "limits".to_string(),
            value: None,
            indent: 10,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "cpu".to_string(),
                value: Some("500m".to_string()),
                indent: 12,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
            }],
        };
        let mut manifest = create_workload_with_resources(vec![requests_node, limits_node]);

        let changes = heal_qos_alignment(&mut manifest, &mut telemetry);
        assert!(changes.is_empty());
    }
}
