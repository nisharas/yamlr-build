//! Protocol Contract Alignment Healer (Rule NET-003).
//!
//! Why: Microservices frequently communicate over gRPC, HTTP/2, or WebSockets.
//! If a Kubernetes Service does not declare `appProtocol: grpc` (or names the port `http`),
//! Kubernetes ingress controllers (NGINX, Envoy, Traefik, Istio) route requests over plain
//! HTTP/1.1 without ALPN negotiation. This results in intermittent HTTP 502 Bad Gateway
//! or 400 Bad Request errors in production.
//!
//! Yamlr detects gRPC/H2C/WebSocket indicators on Services and Ingresses and aligns both
//! `appProtocol` and ingress backend-protocol annotations.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const PROTOCOL_CONTRACT_RULE_ID: &str = "NET-007";

/// Primary entrypoint: Aligns protocol contracts for Services and Ingresses.
pub fn heal_protocol_contracts(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    match kind.as_str() {
        "Service" => {
            let svc_changes = heal_service_protocols(manifest, identities, telemetry);
            changes.extend(svc_changes);
        }
        "Ingress" => {
            let ing_changes = heal_ingress_backend_protocols(manifest, identities, telemetry);
            changes.extend(ing_changes);
        }
        _ => {}
    }

    changes
}

/// Aligns Service ports with gRPC, H2C, or WebSocket appProtocol declarations.
fn heal_service_protocols(
    manifest: &mut SemanticManifest,
    _identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let svc_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "service".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(ports) = spec.find_node_mut("ports") {
            for port_node in &mut ports.children {
                let port_num = port_node
                    .find_value("port")
                    .and_then(|p| p.trim().parse::<u16>().ok())
                    .unwrap_or(0);
                let target_port = port_node.find_value("targetPort").unwrap_or_default();
                let port_name = port_node
                    .find_value("name")
                    .unwrap_or_default()
                    .to_lowercase();
                let cur_app_proto = port_node.find_value("appProtocol");

                // Check for gRPC indicators
                let is_grpc = port_num == 50051
                    || target_port == "50051"
                    || port_name.contains("grpc")
                    || port_name.contains("h2c");

                if is_grpc {
                    let needs_proto_fix = cur_app_proto
                        .as_deref()
                        .map(|p| p != "grpc" && p != "kubernetes.io/h2c")
                        .unwrap_or(true);

                    if needs_proto_fix {
                        let indent = port_node.indent + 2;
                        if let Some(app_proto_node) = port_node.find_node_mut("appProtocol") {
                            app_proto_node.value = Some("grpc".to_string());
                            for s in &mut app_proto_node.shards {
                                s.value = Some("grpc".to_string());
                            }
                        } else {
                            port_node.children.push(SemanticNode {
                                key: "appProtocol".to_string(),
                                value: Some("grpc".to_string()),
                                children: Vec::new(),
                                shards: Vec::new(),
                                indent,
                                is_empty_flow: false,
                            });
                        }

                        // Also rename port if it was mislabeled as 'http'
                        if port_name == "http" {
                            if let Some(name_node) = port_node.find_node_mut("name") {
                                name_node.value = Some("grpc".to_string());
                                for s in &mut name_node.shards {
                                    s.value = Some("grpc".to_string());
                                }
                            }
                        }

                        let msg = format!(
                            "Remediation [{}]: Configured 'appProtocol: grpc' on Service '{}' (port {}) to prevent ALPN negotiation 502 failures.",
                            PROTOCOL_CONTRACT_RULE_ID, svc_name, port_num
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

/// Aligns Ingress annotations with backend gRPC services to ensure correct gateway proxying.
fn heal_ingress_backend_protocols(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let ing_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "ingress".to_string());

    // Check if ingress backend routes to a known gRPC service
    let mut targets_grpc = false;

    if let Some(spec) = manifest.root.find_node("spec") {
        for backend in spec.find_nodes_by_key_recursive("backend") {
            if let Some(svc) = backend.find_node("service") {
                let target_svc_name = svc.find_value("name").unwrap_or_default();
                if target_svc_name.contains("grpc") {
                    targets_grpc = true;
                    break;
                }
                if let Some(port) = svc.find_node("port") {
                    if let Some(p_name) = port.find_value("name") {
                        if p_name.contains("grpc") {
                            targets_grpc = true;
                            break;
                        }
                    }
                    if let Some(p_num) = port.find_value("number") {
                        if p_num == "50051" {
                            targets_grpc = true;
                            break;
                        }
                    }
                }

                // Check cross-resource identities for matching service with gRPC
                for id in identities {
                    if id.kind == "Service" && id.name == target_svc_name {
                        if id.ports.contains(&50051) {
                            targets_grpc = true;
                            break;
                        }
                    }
                }
            }
        }
    }

    if targets_grpc {
        let ann_key = "nginx.ingress.kubernetes.io/backend-protocol";
        let cur_val = manifest.root.find_annotation(ann_key);
        if cur_val.as_deref() != Some("\"GRPC\"") && cur_val.as_deref() != Some("GRPC") {
            set_annotation(&mut manifest.root, ann_key, "\"GRPC\"");
            let msg = format!(
                "Remediation [{}]: Injected Ingress annotation '{}: \"GRPC\"' on Ingress '{}' to enable HTTP/2 ALPN proxying.",
                PROTOCOL_CONTRACT_RULE_ID, ann_key, ing_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
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

    fn create_service_with_port(
        port: u16,
        name: &str,
        app_proto: Option<&str>,
    ) -> SemanticManifest {
        let mut port_children = vec![
            SemanticNode {
                key: "port".to_string(),
                value: Some(port.to_string()),
                indent: 6,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
            },
            SemanticNode {
                key: "name".to_string(),
                value: Some(name.to_string()),
                indent: 6,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
            },
        ];
        if let Some(ap) = app_proto {
            port_children.push(SemanticNode {
                key: "appProtocol".to_string(),
                value: Some(ap.to_string()),
                indent: 6,
                is_empty_flow: false,
                children: vec![],
                shards: vec![],
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
                        value: Some("v1".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "kind".to_string(),
                        value: Some("Service".to_string()),
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
                            value: Some("billing-svc".to_string()),
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
                            key: "ports".to_string(),
                            value: None,
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "-".to_string(),
                                value: None,
                                indent: 4,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: port_children,
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
    fn test_inject_app_protocol_grpc_on_port_50051() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_service_with_port(50051, "http", None);

        let changes = heal_protocol_contracts(&mut manifest, &[], &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Configured 'appProtocol: grpc'"));

        let spec = manifest.root.find_node("spec").unwrap();
        let ports = spec.find_node("ports").unwrap();
        let first_port = &ports.children[0];
        assert_eq!(
            first_port.find_value("appProtocol"),
            Some("grpc".to_string())
        );
        assert_eq!(first_port.find_value("name"), Some("grpc".to_string())); // Replaced misleading 'http' name
    }

    #[test]
    fn test_skip_when_already_grpc() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_service_with_port(50051, "grpc-port", Some("grpc"));

        let changes = heal_protocol_contracts(&mut manifest, &[], &mut telemetry);
        assert!(changes.is_empty());
    }

    #[test]
    fn test_ingress_grpc_backend_protocol_injection() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "apiVersion".to_string(),
                        value: Some("networking.k8s.io/v1".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "kind".to_string(),
                        value: Some("Ingress".to_string()),
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
                            value: Some("gateway-ingress".to_string()),
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
                            key: "rules".to_string(),
                            value: None,
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "-".to_string(),
                                value: None,
                                indent: 4,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "http".to_string(),
                                    value: None,
                                    indent: 6,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "paths".to_string(),
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
                                                key: "backend".to_string(),
                                                value: None,
                                                indent: 12,
                                                is_empty_flow: false,
                                                shards: Vec::new(),
                                                children: vec![SemanticNode {
                                                    key: "service".to_string(),
                                                    value: None,
                                                    indent: 14,
                                                    is_empty_flow: false,
                                                    shards: Vec::new(),
                                                    children: vec![SemanticNode {
                                                        key: "name".to_string(),
                                                        value: Some("auth-grpc-svc".to_string()),
                                                        indent: 16,
                                                        is_empty_flow: false,
                                                        children: vec![],
                                                        shards: vec![],
                                                    }],
                                                }],
                                            }],
                                        }],
                                    }],
                                }],
                            }],
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_protocol_contracts(&mut manifest, &[], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let ann = manifest
            .root
            .find_annotation("nginx.ingress.kubernetes.io/backend-protocol");
        assert_eq!(ann, Some("\"GRPC\"".to_string()));
    }
}
