//! Istio Service Mesh Manifest Auto-Healer (Rule ECO-001).
//!
//! Why: Istio manifests (VirtualService, DestinationRule, Gateway) have strict schema rules
//! and semantic invariants. Deprecated API versions (v1alpha3), mismatched route weights
//! (must sum to 100), invalid TLS mode casing, and empty host definitions break Envoy
//! configuration generation in Pilot/Istiod, causing silent traffic drops or cluster routing errors.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const ISTIO_RULE_ID: &str = "ECO-001";

/// Primary entrypoint: Heals Istio VirtualService, DestinationRule, and Gateway manifests.
pub fn heal_istio_manifests(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    // Fast return if not an Istio networking resource
    if !api_version.starts_with("networking.istio.io")
        && !api_version.starts_with("install.istio.io")
    {
        return changes;
    }

    // 1. Upgrade deprecated v1alpha3 to v1
    if api_version == "networking.istio.io/v1alpha3" {
        if let Some(api_node) = manifest.root.find_node_mut("apiVersion") {
            api_node.value = Some("networking.istio.io/v1".to_string());
            for s in &mut api_node.shards {
                s.value = Some("networking.istio.io/v1".to_string());
            }
            let msg = format!(
                "Remediation [{}]: Upgraded deprecated Istio API 'networking.istio.io/v1alpha3' -> 'networking.istio.io/v1' on {}.",
                ISTIO_RULE_ID, kind
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    match kind.as_str() {
        "VirtualService" => changes.extend(heal_virtual_service(manifest, telemetry)),
        "DestinationRule" => changes.extend(heal_destination_rule(manifest, telemetry)),
        "Gateway" => changes.extend(heal_gateway(manifest, telemetry)),
        _ => {}
    }

    changes
}

fn heal_virtual_service(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let spec = match manifest.root.find_node_mut("spec") {
        Some(s) => s,
        None => return changes,
    };

    // A. Validate hosts list
    if let Some(hosts_node) = spec.find_node_mut("hosts") {
        if hosts_node.children.is_empty() && hosts_node.value.is_none() {
            let indent = hosts_node.indent + 2;
            hosts_node.children.push(SemanticNode {
                key: "-".to_string(),
                value: Some("\"*\"".to_string()),
                children: Vec::new(),
                shards: Vec::new(),
                indent,
                is_empty_flow: false,
            });
            let msg = format!(
                "Remediation [{}]: Injected default wildcard host '*' into empty VirtualService hosts list.",
                ISTIO_RULE_ID
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    // B. Route weights balance: if multiple destinations in a route, ensure weights sum to 100
    for http_route in spec.find_nodes_by_key_recursive_mut("http") {
        for route_item in &mut http_route.children {
            if let Some(route_list) = route_item.find_node_mut("route") {
                let destinations = &mut route_list.children;
                if destinations.len() > 1 {
                    let mut total_weight: i32 = 0;
                    let mut weight_nodes_indices = Vec::new();

                    for (idx, dst) in destinations.iter().enumerate() {
                        if let Some(w_node) = dst.find_node("weight") {
                            if let Some(ref val) = w_node.value {
                                let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                                if let Ok(w) = clean.parse::<i32>() {
                                    total_weight += w;
                                    weight_nodes_indices.push((idx, w));
                                }
                            }
                        }
                    }

                    if !weight_nodes_indices.is_empty() && total_weight != 100 {
                        let even_split = 100 / destinations.len() as i32;
                        let remainder = 100 % destinations.len() as i32;

                        for (i, dst) in destinations.iter_mut().enumerate() {
                            let assigned = if i == 0 {
                                even_split + remainder
                            } else {
                                even_split
                            };
                            if let Some(w_node) = dst.find_node_mut("weight") {
                                w_node.value = Some(assigned.to_string());
                                for s in &mut w_node.shards {
                                    s.value = Some(assigned.to_string());
                                }
                            }
                        }

                        let msg = format!(
                            "Remediation [{}]: Rebalanced route destination weights summing to {}% -> 100% across {} destinations.",
                            ISTIO_RULE_ID, total_weight, destinations.len()
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

fn heal_destination_rule(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let spec = match manifest.root.find_node_mut("spec") {
        Some(s) => s,
        None => return changes,
    };

    // A. Validate trafficPolicy.tls.mode
    for tls_node in spec.find_nodes_by_key_recursive_mut("tls") {
        if let Some(mode_node) = tls_node.find_node_mut("mode") {
            let mut needs_fix = None;
            if let Some(ref val) = mode_node.value {
                let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                let upper = clean.to_uppercase();
                let normalized = match upper.as_str() {
                    "DISABLE" => "DISABLE",
                    "SIMPLE" => "SIMPLE",
                    "MUTUAL" => "MUTUAL",
                    "ISTIO_MUTUAL" | "ISTIOMUTUAL" | "ISTIO-MUTUAL" => "ISTIO_MUTUAL",
                    _ => "",
                };

                if !normalized.is_empty() && clean != normalized {
                    needs_fix = Some((clean.to_string(), normalized.to_string()));
                }
            }

            if let Some((old_val, new_val)) = needs_fix {
                mode_node.value = Some(new_val.clone());
                for s in &mut mode_node.shards {
                    s.value = Some(new_val.clone());
                }
                let msg = format!(
                    "Remediation [{}]: Normalized DestinationRule TLS mode '{}' -> '{}'.",
                    ISTIO_RULE_ID, old_val, new_val
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    changes
}

fn heal_gateway(manifest: &mut SemanticManifest, telemetry: &mut NativeTelemetry) -> Vec<String> {
    let mut changes = Vec::new();
    let spec = match manifest.root.find_node_mut("spec") {
        Some(s) => s,
        None => return changes,
    };

    // Validate servers port protocols (HTTP, HTTPS, GRPC, HTTP2, MONGO, TCP, TLS)
    for server_node in spec.find_nodes_by_key_recursive_mut("servers") {
        for server in &mut server_node.children {
            if let Some(port_node) = server.find_node_mut("port") {
                if let Some(proto_node) = port_node.find_node_mut("protocol") {
                    let mut needs_fix = None;
                    if let Some(ref val) = proto_node.value {
                        let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                        let upper = clean.to_uppercase();
                        if (upper == "HTTP"
                            || upper == "HTTPS"
                            || upper == "GRPC"
                            || upper == "TCP"
                            || upper == "TLS")
                            && clean != upper
                        {
                            needs_fix = Some((clean.to_string(), upper));
                        }
                    }
                    if let Some((old_val, new_val)) = needs_fix {
                        proto_node.value = Some(new_val.clone());
                        for s in &mut proto_node.shards {
                            s.value = Some(new_val.clone());
                        }
                        let msg = format!(
                            "Remediation [{}]: Normalized Gateway server protocol '{}' -> '{}'.",
                            ISTIO_RULE_ID, old_val, new_val
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
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_heal_deprecated_istio_api_version() {
        let yaml = r#"
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
    - reviews.prod.svc.cluster.local
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_istio_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 1);
        assert_eq!(
            manifest.root.find_value("apiVersion"),
            Some("networking.istio.io/v1".to_string())
        );
    }

    #[test]
    fn test_heal_virtual_service_route_weights() {
        let yaml = r#"
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
    - reviews
  http:
    - route:
        - destination:
            host: reviews
            subset: v1
          weight: 40
        - destination:
            host: reviews
            subset: v2
          weight: 40
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_istio_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Rebalanced route destination weights summing to 80% -> 100%"));
    }

    #[test]
    fn test_heal_destination_rule_tls_mode() {
        let yaml = r#"
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: ratings-dr
spec:
  host: ratings
  trafficPolicy:
    tls:
      mode: istio-mutual
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_istio_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 1);
        assert!(changes[0]
            .contains("Normalized DestinationRule TLS mode 'istio-mutual' -> 'ISTIO_MUTUAL'"));
    }
}
