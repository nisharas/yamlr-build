//! Service appProtocol Healer & Modernizer (Rule NET-009).
//!
//! Why: In Kubernetes 1.20+, Service port `appProtocol` allows ingress controllers,
//! service meshes (Istio, Linkerd, Envoy), and Gateway API to configure layer-7 routing
//! correctly without relying on ambiguous heuristic protocol sniffing.
//! Missing or mis-cased `appProtocol` causes 502/503 errors and routing failures.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const APP_PROTOCOL_RULE_ID: &str = "NET-009";

/// Infers the layer-7 application protocol from port name and port number.
pub fn infer_app_protocol(
    port_name: Option<&str>,
    port_number: Option<i32>,
) -> Option<&'static str> {
    if let Some(name) = port_name {
        let name_lower = name.to_lowercase();
        if name_lower.contains("grpc") {
            return Some("grpc");
        }
        if name_lower.contains("https") {
            return Some("https");
        }
        if name_lower.contains("http") {
            return Some("http");
        }
        if name_lower.contains("dns") {
            return Some("dns");
        }
        if name_lower.contains("tcp") {
            return Some("tcp");
        }
        if name_lower.contains("udp") {
            return Some("udp");
        }
    }

    if let Some(num) = port_number {
        match num {
            80 | 8080 | 3000 | 5000 | 8000 => Some("http"),
            443 | 8443 => Some("https"),
            53 => Some("dns"),
            _ => None,
        }
    } else {
        None
    }
}

/// Aligns or injects missing `appProtocol` on Service ports.
pub fn heal_app_protocols(
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
        .unwrap_or_else(|| "unnamed".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(ports) = spec.find_node_mut("ports") {
            for port_node in &mut ports.children {
                let current_app_proto = port_node.find_value("appProtocol");
                let port_name = port_node.find_value("name");
                let port_num = port_node
                    .find_value("port")
                    .and_then(|v| v.parse::<i32>().ok());

                if let Some(ref proto) = current_app_proto {
                    let proto_clean = proto.trim().trim_matches('"').trim_matches('\'');
                    let proto_lower = proto_clean.to_lowercase();
                    if proto_clean != proto_lower {
                        if let Some(node) = port_node.find_node_mut("appProtocol") {
                            node.value = Some(proto_lower.clone());
                            for s in &mut node.shards {
                                s.value = Some(proto_lower.clone());
                            }
                            let msg = format!(
                                "Remediation [{}]: Normalized appProtocol '{}' -> '{}' in Service '{}'.",
                                APP_PROTOCOL_RULE_ID, proto_clean, proto_lower, svc_name
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                } else if let Some(inferred) = infer_app_protocol(port_name.as_deref(), port_num) {
                    let indent = port_node.indent + 2;
                    port_node.children.push(SemanticNode {
                        key: "appProtocol".to_string(),
                        value: Some(inferred.to_string()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent,
                        is_empty_flow: false,
                    });
                    let msg = format!(
                        "Remediation [{}]: Injected appProtocol: '{}' on Service '{}' port {}.",
                        APP_PROTOCOL_RULE_ID,
                        inferred,
                        svc_name,
                        port_num.unwrap_or(0)
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
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
    fn test_infer_protocols() {
        assert_eq!(infer_app_protocol(Some("http-web"), None), Some("http"));
        assert_eq!(
            infer_app_protocol(Some("https-traffic"), None),
            Some("https")
        );
        assert_eq!(infer_app_protocol(Some("grpc-service"), None), Some("grpc"));
        assert_eq!(infer_app_protocol(None, Some(80)), Some("http"));
        assert_eq!(infer_app_protocol(None, Some(443)), Some("https"));
    }

    #[test]
    fn test_inject_missing_app_protocol() {
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
                        children: vec![SemanticNode {
                            key: "ports".into(),
                            value: None,
                            children: vec![SemanticNode {
                                key: "-".into(),
                                value: None,
                                children: vec![
                                    SemanticNode {
                                        key: "name".into(),
                                        value: Some("web".into()),
                                        children: vec![],
                                        shards: vec![],
                                        indent: 6,
                                        is_empty_flow: false,
                                    },
                                    SemanticNode {
                                        key: "port".into(),
                                        value: Some("80".into()),
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
        let changes = heal_app_protocols(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        let ports = spec.find_node("ports").unwrap();
        let port_0 = &ports.children[0];
        assert_eq!(port_0.find_value("appProtocol"), Some("http".to_string()));
    }
}
