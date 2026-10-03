//! Service targetPort Alignment Healer (Rule NET-011).
//!
//! Why: In Kubernetes Services, misconfigured `spec.ports[].targetPort` (whether a typo in a named port
//! or an unaligned numeric port) causes traffic blackholes where the Service has endpoints with no
//! matching container listener.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const TARGET_PORT_RULE_ID: &str = "NET-011";
pub const PORT_SIMILARITY_THRESHOLD: f64 = 0.60;

/// Aligns Service targetPort names and numbers against container ports in matched workloads.
pub fn heal_service_target_ports(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return changes;
    }

    let svc_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-svc".to_string());

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    // Extract selector map
    let mut selector_map = std::collections::HashMap::new();
    if let Some(spec) = manifest.root.find_node("spec") {
        if let Some(sel_node) = spec.find_node("selector") {
            for child in &sel_node.children {
                if let Some(ref val) = child.value {
                    selector_map.insert(
                        child.key.clone(),
                        val.trim_matches('"').trim_matches('\'').to_string(),
                    );
                }
            }
        }
    }

    if selector_map.is_empty() {
        return changes;
    }

    // Find best matching workload in namespace
    let matched_workload = identities
        .iter()
        .filter(|id| {
            (id.namespace == ns || id.namespace.is_empty() || id.namespace == "default")
                && crate::healers::selector_healer::WORKLOAD_KINDS.contains(&id.kind.as_str())
        })
        .max_by(|a, b| {
            let sim_a = crate::healers::selector_healer::calculate_label_similarity(
                &selector_map,
                &a.labels,
            );
            let sim_b = crate::healers::selector_healer::calculate_label_similarity(
                &selector_map,
                &b.labels,
            );
            sim_a
                .partial_cmp(&sim_b)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

    let target_workload = match matched_workload {
        Some(w)
            if crate::healers::selector_healer::calculate_label_similarity(
                &selector_map,
                &w.labels,
            ) >= 0.70 =>
        {
            w
        }
        _ => return changes,
    };

    let available_ports = &target_workload.ports;
    if available_ports.is_empty() {
        return changes;
    }

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(ports_node) = spec.find_node_mut("ports") {
            for port_entry in &mut ports_node.children {
                if let Some(tp_node) = port_entry.find_node_mut("targetPort") {
                    let current = tp_node.value.clone().unwrap_or_default();
                    let clean = current.trim().trim_matches('"').trim_matches('\'');

                    let port_defs = &target_workload.container_port_defs;

                    // Check if numeric
                    if let Ok(num) = clean.parse::<i32>() {
                        // Numeric check: If exactly 1 container port exists and it differs from targetPort
                        if available_ports.len() == 1
                            && available_ports[0] > 0
                            && available_ports[0] != num
                        {
                            let target_num = available_ports[0];
                            tp_node.value = Some(target_num.to_string());
                            for s in &mut tp_node.shards {
                                s.value = Some(target_num.to_string());
                            }
                            let msg = format!(
                                "Remediation [{}]: Aligned Service '{}' targetPort {} -> {} to match workload '{}'.",
                                TARGET_PORT_RULE_ID, svc_name, num, target_num, target_workload.name
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    } else {
                        // Named port check: Fuzzy match against available container port names
                        let names: Vec<&str> =
                            port_defs.iter().filter_map(|(n, _)| n.as_deref()).collect();

                        if !names.contains(&clean) && !names.is_empty() {
                            let mut best_target = None;
                            let mut best_ratio = 0.0;
                            for n in names {
                                let ratio =
                                    crate::healers::selector_healer::similarity_ratio(clean, n);
                                if ratio >= PORT_SIMILARITY_THRESHOLD && ratio > best_ratio {
                                    best_ratio = ratio;
                                    best_target = Some(n);
                                }
                            }

                            if let Some(target) = best_target {
                                tp_node.value = Some(target.to_string());
                                for s in &mut tp_node.shards {
                                    s.value = Some(target.to_string());
                                }
                                let msg = format!(
                                    "Remediation [{}]: Aligned Service '{}' targetPort name '{}' -> '{}' (similarity: {:.2}).",
                                    TARGET_PORT_RULE_ID, svc_name, clean, target, best_ratio
                                );
                                native_record_healing_impact(telemetry, &msg);
                                changes.push(msg);
                            }
                        }
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
    use crate::models::SemanticNode;

    #[test]
    fn test_align_named_target_port_typo() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Service".into()),
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
                                key: "selector".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "app".into(),
                                    value: Some("api-server".into()),
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
                                key: "ports".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "-".into(),
                                    value: None,
                                    children: vec![
                                        SemanticNode {
                                            key: "port".into(),
                                            value: Some("80".into()),
                                            children: vec![],
                                            shards: vec![],
                                            indent: 6,
                                            is_empty_flow: false,
                                        },
                                        SemanticNode {
                                            key: "targetPort".into(),
                                            value: Some("http-sv".into()),
                                            children: vec![],
                                            shards: vec![],
                                            indent: 6,
                                            is_empty_flow: false,
                                        },
                                    ],
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

        let mut labels = std::collections::HashMap::new();
        labels.insert("app".into(), "api-server".into());

        let target_workload = NativeIdentity {
            kind: "Deployment".into(),
            name: "api-server".into(),
            namespace: "default".into(),
            labels,
            ports: vec![8080],
            container_port_defs: vec![(Some("http-svc".into()), 8080)],
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_service_target_ports(&mut manifest, &[target_workload], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        let ports = spec.find_node("ports").unwrap();
        let port_0 = &ports.children[0];
        assert_eq!(
            port_0.find_value("targetPort"),
            Some("http-svc".to_string())
        );
    }
}
