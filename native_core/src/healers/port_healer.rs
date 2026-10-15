//! Service Named-Port & ContainerPort Fuzzy Alignment Engine (Feature 5 of 15).
//!
//! Why: Kubernetes Services that reference the wrong `targetPort` fail silently:
//! traffic is sent nowhere (0 endpoints or connection refused).
//! This module resolves:
//! 1. Strategy A: Single containerPort auto-alignment (e.g. Service targetPort 80 vs Container 8080).
//! 2. Strategy B: Named-port fuzzy matching (e.g. Service targetPort 'http-svc' vs Container port name 'http').

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub static NAMED_PORT_SIMILARITY_THRESHOLD: f64 = 0.60;

#[derive(Debug, Clone)]
pub struct ContainerPortDef {
    pub name: Option<String>,
    pub port_number: i32,
}

/// Helper: Extracts container ports (names and numbers) from a SemanticNode tree.
pub fn extract_container_ports_from_node(node: &SemanticNode) -> Vec<ContainerPortDef> {
    let mut ports = Vec::new();
    for c_node in node.find_nodes_by_key_recursive("containers") {
        for container in &c_node.children {
            if let Some(ports_node) = container.find_node("ports") {
                for port_item in &ports_node.children {
                    let name = port_item.find_value("name");
                    let port_number = port_item
                        .find_value("containerPort")
                        .and_then(|v| v.parse::<i32>().ok())
                        .unwrap_or(0);
                    if port_number > 0 || name.is_some() {
                        ports.push(ContainerPortDef { name, port_number });
                    }
                }
            }
        }
    }
    ports
}

/// Aligns a single Service port entry against available workload container ports.
pub fn align_service_port_entry(
    port_node: &mut SemanticNode,
    available_ports: &[ContainerPortDef],
    svc_name: &str,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) -> bool {
    let target_port_node = port_node.find_node_mut("targetPort");
    if target_port_node.is_none() {
        return false;
    }

    let tp = target_port_node.unwrap();
    let current_val = match &tp.value {
        Some(v) => v.trim().trim_matches(|c| c == '\'' || c == '"').to_string(),
        None => return false,
    };

    // Strategy A: Numeric port check
    if let Ok(num) = current_val.parse::<i32>() {
        // If container has exactly 1 port and it differs from targetPort
        if available_ports.len() == 1 {
            let actual = available_ports[0].port_number;
            if actual > 0 && actual != num {
                tp.value = Some(actual.to_string());
                for s in &mut tp.shards {
                    s.value = Some(actual.to_string());
                }
                let msg = format!(
                    "Remediation [NET-004]: Aligned Service '{}' targetPort {} -> {} to match single container port.",
                    svc_name, num, actual
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
                return true;
            }
        }
        return false;
    }

    // Strategy B: Named-port fuzzy matching
    let mut best_match: Option<&ContainerPortDef> = None;
    let mut best_ratio = 0.0;

    for cp in available_ports {
        if let Some(ref c_name) = cp.name {
            let sim = crate::healers::selector_healer::similarity_ratio(&current_val, c_name);
            let prefix_match = current_val.starts_with(c_name) || c_name.starts_with(&current_val);
            let ratio = if prefix_match { sim.max(0.70) } else { sim };
            if ratio >= NAMED_PORT_SIMILARITY_THRESHOLD && ratio > best_ratio {
                best_ratio = ratio;
                best_match = Some(cp);
            }
        }
    }

    if let Some(matched) = best_match {
        let matched_name = matched.name.as_ref().unwrap();
        if current_val != *matched_name {
            tp.value = Some(matched_name.clone());
            for s in &mut tp.shards {
                s.value = Some(matched_name.clone());
            }
            let msg = format!(
                "Remediation [NET-003]: Aligned fuzzy named targetPort '{}' -> '{}' for Service '{}' (score: {:.2}).",
                current_val, matched_name, svc_name, best_ratio
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
            return true;
        }
    }

    false
}

/// Primary Entrypoint: Aligns Service targetPorts with workload ports across manifest or identities.
pub fn heal_service_ports(
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
        .unwrap_or_else(|| "unknown".to_string());

    // 1. Try to extract container ports from the same manifest (multi-resource doc)
    let mut available_ports = extract_container_ports_from_node(&manifest.root);

    // 2. If empty, fall back to identities
    if available_ports.is_empty() {
        for id in identities {
            if crate::healers::selector_healer::WORKLOAD_KINDS.contains(&id.kind.as_str()) {
                for &p in &id.ports {
                    available_ports.push(ContainerPortDef {
                        name: None,
                        port_number: p,
                    });
                }
            }
        }
    }

    // Trap 29: Docker Compose port range syntax resolution in Kubernetes (e.g. `port: 8000-8010`)
    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(ports_node) = spec.find_node_mut("ports") {
            for port_item in &mut ports_node.children {
                for key_name in ["port", "targetPort", "containerPort"] {
                    if let Some(p_node) = port_item.find_node_mut(key_name) {
                        let val_clone = p_node.value.clone();
                        if let Some(val) = val_clone {
                            let unquoted = val.trim().trim_matches('"').trim_matches('\'').to_string();
                            if unquoted.contains('-') && !unquoted.starts_with('-') {
                                if let Some((start_p, _)) = unquoted.split_once('-') {
                                    if let Ok(p_num) = start_p.trim().parse::<i32>() {
                                        p_node.value = Some(p_num.to_string());
                                        let msg = format!(
                                            "Remediation [NET-012]: Resolved port range '{}' -> single port '{}' under Service '{}' {}.",
                                            unquoted, p_num, svc_name, key_name
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
        }
    }

    // Trap 53 / Rule NET-014: nodePort string unquoting and range validation (30000 - 32767)
    let np_changes = heal_service_node_ports(manifest, telemetry);
    changes.extend(np_changes);

    if available_ports.is_empty() {
        return changes;
    }

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(ports_node) = spec.find_node_mut("ports") {
            for port_item in &mut ports_node.children {

                align_service_port_entry(
                    port_item,
                    &available_ports,
                    &svc_name,
                    telemetry,
                    &mut changes,
                );
            }
        }
    }

    changes
}

pub const RULE_NET_014: &str = "NET-014";

/// Rule NET-014 (Trap 53): Validates, unquotes, and prunes invalid out-of-range `nodePort` values.
///
/// Why: In Kubernetes `Service`, `spec.ports[*].nodePort` must be:
/// 1. Strict integer scalar (quoted `"30080"` causes admission rejection).
/// 2. Within the cluster's nodePort allocation range (default: 30000 - 32767).
///
/// If an author declares a low port (e.g. `nodePort: 8080`, `nodePort: 80`), kube-apiserver immediately
/// rejects the manifest with: `provided port is not in the valid range. The range of valid ports is 30000-32767`.
///
/// Zero-assumption:
/// - If stringified and within 30000..=32767, unquote it to a standard integer.
/// - If outside 30000..=32767, prune the explicit `nodePort` field so Kubernetes dynamically assigns
///   a free port in the valid range without admission rejection.
pub fn heal_service_node_ports(
    manifest: &mut SemanticManifest,
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
        .unwrap_or_else(|| "unnamed-service".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(ports_node) = spec.find_node_mut("ports") {
            for port_item in &mut ports_node.children {
                let mut should_remove_node_port = false;

                if let Some(np_node) = port_item.find_node_mut("nodePort") {
                    if let Some(val) = &np_node.value {
                        let trimmed = val.trim();
                        let clean = trimmed.trim_matches(|c| c == '\'' || c == '"');
                        if let Ok(np_num) = clean.parse::<i32>() {
                            if (30000..=32767).contains(&np_num) {
                                // Valid range: unquote if stringified
                                let canonical = np_num.to_string();
                                if *val != canonical {
                                    let old_val = val.clone();
                                    np_node.value = Some(canonical.clone());
                                    for s in &mut np_node.shards {
                                        s.value = Some(canonical.clone());
                                    }
                                    let msg = format!(
                                        "Remediation [{}]: Unquoted integer nodePort '{}' -> {} on Service '{}'.",
                                        RULE_NET_014, old_val, canonical, svc_name
                                    );
                                    native_record_healing_impact(telemetry, &msg);
                                    changes.push(msg);
                                }
                            } else {
                                // Invalid range (< 30000 or > 32767): flag for removal so K8s auto-assigns
                                should_remove_node_port = true;
                            }
                        }
                    }
                }

                if should_remove_node_port {
                    if let Some(idx) = port_item.children.iter().position(|c| c.key == "nodePort") {
                        let removed = port_item.children.remove(idx);
                        let old_val = removed.value.unwrap_or_default();
                        let msg = format!(
                            "Remediation [{}]: Pruned out-of-range nodePort '{}' (valid range: 30000-32767) on Service '{}' to allow dynamic cluster allocation.",
                            RULE_NET_014, old_val, svc_name
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

    #[test]
    fn test_named_port_fuzzy_match() {
        let ports = vec![
            ContainerPortDef {
                name: Some("http".to_string()),
                port_number: 80,
            },
            ContainerPortDef {
                name: Some("metrics".to_string()),
                port_number: 9090,
            },
        ];

        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();

        let mut port_entry = SemanticNode {
            key: "-".to_string(),
            value: None,
            indent: 4,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![
                SemanticNode {
                    key: "port".to_string(),
                    value: Some("80".to_string()),
                    indent: 6,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
                SemanticNode {
                    key: "targetPort".to_string(),
                    value: Some("http-svc".to_string()), // Typo/misnamed
                    indent: 6,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
            ],
        };

        let modified = align_service_port_entry(
            &mut port_entry,
            &ports,
            "web-svc",
            &mut telemetry,
            &mut changes,
        );
        assert!(modified);
        let tp = port_entry.find_node("targetPort").unwrap();
        assert_eq!(tp.value, Some("http".to_string()));
    }

    #[test]
    fn test_heal_port_range_trap_29() {
        let input_yaml = r#"apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  ports:
  - port: 8000-8010
    targetPort: 8000-8010
"#;
        let shards = crate::sharder::native_shard(input_yaml);
        let mut manifest = crate::structurer::native_structurize(shards);
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_service_ports(&mut manifest, &[], &mut telemetry);

        assert!(!changes.is_empty());
        let spec = manifest.root.find_node("spec").unwrap();
        let ports = spec.find_node("ports").unwrap();
        let first_item = &ports.children[0];
        assert_eq!(first_item.find_value("port"), Some("8000".to_string()));
        assert_eq!(first_item.find_value("targetPort"), Some("8000".to_string()));
    }

    #[test]
    fn test_heal_service_node_ports_unquoting_and_pruning() {
        let input_yaml = r#"apiVersion: v1
kind: Service
metadata:
  name: nodeport-svc
spec:
  type: NodePort
  ports:
  - name: web
    port: 80
    targetPort: 80
    nodePort: "30080"
  - name: invalid-low
    port: 8080
    targetPort: 8080
    nodePort: 8080
"#;
        let shards = crate::sharder::native_shard(input_yaml);
        let mut manifest = crate::structurer::native_structurize(shards);
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_service_ports(&mut manifest, &[], &mut telemetry);

        assert_eq!(changes.len(), 2);
        assert!(changes.iter().any(|c| c.contains("Unquoted integer nodePort '\"30080\"' -> 30080")));
        assert!(changes.iter().any(|c| c.contains("Pruned out-of-range nodePort '8080'")));

        let spec = manifest.root.find_node("spec").unwrap();
        let ports = spec.find_node("ports").unwrap();
        assert_eq!(ports.children[0].find_value("nodePort"), Some("30080".to_string()));
        assert!(ports.children[1].find_node("nodePort").is_none());
    }
}

