//! NetworkPolicy Egress DNS Blackout Preventer (Rule SEC-010).
//!
//! Why: In Kubernetes, applying a NetworkPolicy with `policyTypes: [Egress]` without an explicit
//! allow rule for DNS (port 53 UDP/TCP) creates a complete DNS blackout. Pods become unable to resolve
//! internal services or external APIs, triggering silent catastrophic application failure.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const EGRESS_DNS_RULE_ID: &str = "SEC-010";

/// Checks if an egress node already contains a port 53 allow rule.
fn has_dns_egress_rule(egress_node: &SemanticNode) -> bool {
    for rule in &egress_node.children {
        if let Some(ports_node) = rule.find_node("ports") {
            for port_entry in &ports_node.children {
                if let Some(p) = port_entry.find_value("port") {
                    if p.trim().trim_matches('"') == "53" {
                        return true;
                    }
                }
            }
        }
    }
    false
}

/// Heals NetworkPolicy egress to ensure DNS resolution is never blacked out.
pub fn heal_network_policy_egress(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "NetworkPolicy" {
        return changes;
    }

    let policy_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-netpol".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        // Check if Egress is in policyTypes
        let has_egress_policy_type = spec
            .find_node("policyTypes")
            .map(|pt| {
                pt.children.iter().any(|c| {
                    c.value
                        .as_deref()
                        .or(Some(&c.key))
                        .map_or(false, |v| v.contains("Egress"))
                })
            })
            .unwrap_or(false);

        if has_egress_policy_type {
            let needs_injection = match spec.find_node("egress") {
                Some(egress_node) => !has_dns_egress_rule(egress_node),
                None => true,
            };

            if needs_injection {
                if let Some(egress_node) = spec.find_node_mut("egress") {
                    let indent = egress_node.indent + 2;
                    egress_node.children.push(SemanticNode {
                        key: "-".to_string(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "ports".to_string(),
                            value: None,
                            children: vec![
                                SemanticNode {
                                    key: "-".to_string(),
                                    value: None,
                                    children: vec![
                                        SemanticNode {
                                            key: "protocol".to_string(),
                                            value: Some("UDP".to_string()),
                                            children: vec![],
                                            shards: vec![],
                                            indent: indent + 6,
                                            is_empty_flow: false,
                                        },
                                        SemanticNode {
                                            key: "port".to_string(),
                                            value: Some("53".to_string()),
                                            children: vec![],
                                            shards: vec![],
                                            indent: indent + 6,
                                            is_empty_flow: false,
                                        },
                                    ],
                                    shards: vec![],
                                    indent: indent + 4,
                                    is_empty_flow: false,
                                },
                                SemanticNode {
                                    key: "-".to_string(),
                                    value: None,
                                    children: vec![
                                        SemanticNode {
                                            key: "protocol".to_string(),
                                            value: Some("TCP".to_string()),
                                            children: vec![],
                                            shards: vec![],
                                            indent: indent + 6,
                                            is_empty_flow: false,
                                        },
                                        SemanticNode {
                                            key: "port".to_string(),
                                            value: Some("53".to_string()),
                                            children: vec![],
                                            shards: vec![],
                                            indent: indent + 6,
                                            is_empty_flow: false,
                                        },
                                    ],
                                    shards: vec![],
                                    indent: indent + 4,
                                    is_empty_flow: false,
                                },
                            ],
                            shards: vec![],
                            indent: indent + 2,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent,
                        is_empty_flow: false,
                    });
                } else {
                    let indent = spec.indent + 2;
                    spec.children.push(SemanticNode {
                        key: "egress".to_string(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "-".to_string(),
                            value: None,
                            children: vec![SemanticNode {
                                key: "ports".to_string(),
                                value: None,
                                children: vec![
                                    SemanticNode {
                                        key: "-".to_string(),
                                        value: None,
                                        children: vec![
                                            SemanticNode {
                                                key: "protocol".to_string(),
                                                value: Some("UDP".to_string()),
                                                children: vec![],
                                                shards: vec![],
                                                indent: indent + 6,
                                                is_empty_flow: false,
                                            },
                                            SemanticNode {
                                                key: "port".to_string(),
                                                value: Some("53".to_string()),
                                                children: vec![],
                                                shards: vec![],
                                                indent: indent + 6,
                                                is_empty_flow: false,
                                            },
                                        ],
                                        shards: vec![],
                                        indent: indent + 4,
                                        is_empty_flow: false,
                                    },
                                    SemanticNode {
                                        key: "-".to_string(),
                                        value: None,
                                        children: vec![
                                            SemanticNode {
                                                key: "protocol".to_string(),
                                                value: Some("TCP".to_string()),
                                                children: vec![],
                                                shards: vec![],
                                                indent: indent + 6,
                                                is_empty_flow: false,
                                            },
                                            SemanticNode {
                                                key: "port".to_string(),
                                                value: Some("53".to_string()),
                                                children: vec![],
                                                shards: vec![],
                                                indent: indent + 6,
                                                is_empty_flow: false,
                                            },
                                        ],
                                        shards: vec![],
                                        indent: indent + 4,
                                        is_empty_flow: false,
                                    },
                                ],
                                shards: vec![],
                                indent: indent + 2,
                                is_empty_flow: false,
                            }],
                            shards: vec![],
                            indent,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent,
                        is_empty_flow: false,
                    });
                }

                let msg = format!(
                    "Remediation [{}]: Injected essential DNS (port 53 UDP/TCP) allow rule into NetworkPolicy '{}' egress.",
                    EGRESS_DNS_RULE_ID, policy_name
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

    #[test]
    fn test_inject_dns_egress_rule() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("NetworkPolicy".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "policyTypes".into(),
                            value: None,
                            children: vec![SemanticNode {
                                key: "-".into(),
                                value: Some("Egress".into()),
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

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_network_policy_egress(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        let egress = spec.find_node("egress").unwrap();
        assert!(has_dns_egress_rule(egress));
    }
}
