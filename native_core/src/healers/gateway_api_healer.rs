//! Gateway API HTTPRoute Modernizer (Feature 21).
//!
//! Why: Kubernetes Ingress is entering maintenance in favor of Gateway API
//! (`gateway.networking.k8s.io/v1`). Teams need automated migration from
//! Ingress manifests to modern `HTTPRoute` resources without manually rewriting rules.

use crate::models::{NativeTelemetry, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const GATEWAY_API_RULE_ID: &str = "MIG-002";

#[derive(Debug, Clone)]
pub struct IngressPathRule {
    pub path: String,
    pub path_type: String,
    pub service_name: String,
    pub service_port: i32,
}

#[derive(Debug, Clone)]
pub struct IngressHostRule {
    pub host: Option<String>,
    pub paths: Vec<IngressPathRule>,
}

/// Helper: Extracts routing rules from an Ingress SemanticNode.
pub fn extract_ingress_rules(node: &SemanticNode) -> Vec<IngressHostRule> {
    let mut host_rules = Vec::new();
    let kind = node.find_value("kind").unwrap_or_default();
    if kind != "Ingress" {
        return host_rules;
    }

    if let Some(spec) = node.find_node("spec") {
        if let Some(rules) = spec.find_node("rules") {
            for r in &rules.children {
                let host = r.find_value("host");
                let mut paths = Vec::new();

                if let Some(http) = r.find_node("http") {
                    if let Some(paths_node) = http.find_node("paths") {
                        for p in &paths_node.children {
                            let path = p.find_value("path").unwrap_or_else(|| "/".to_string());
                            let path_type = p
                                .find_value("pathType")
                                .unwrap_or_else(|| "Prefix".to_string());
                            let mut svc_name = String::new();
                            let mut svc_port = 80;

                            if let Some(backend) = p.find_node("backend") {
                                if let Some(svc) = backend.find_node("service") {
                                    svc_name = svc.find_value("name").unwrap_or_default();
                                    if let Some(port) = svc.find_node("port") {
                                        svc_port = port
                                            .find_value("number")
                                            .and_then(|v| v.parse::<i32>().ok())
                                            .unwrap_or(80);
                                    }
                                }
                            }

                            if !svc_name.is_empty() {
                                paths.push(IngressPathRule {
                                    path,
                                    path_type,
                                    service_name: svc_name,
                                    service_port: svc_port,
                                });
                            }
                        }
                    }
                }

                host_rules.push(IngressHostRule { host, paths });
            }
        }
    }

    host_rules
}

/// Synthesizes a canonical Gateway API `HTTPRoute` YAML string from an Ingress node.
pub fn convert_ingress_to_httproute(
    node: &SemanticNode,
    telemetry: &mut NativeTelemetry,
) -> Option<String> {
    let kind = node.find_value("kind").unwrap_or_default();
    if kind != "Ingress" {
        return None;
    }

    let meta = node.find_node("metadata")?;
    let name = meta
        .find_value("name")
        .unwrap_or_else(|| "migrated-route".to_string());
    let ns = meta
        .find_value("namespace")
        .unwrap_or_else(|| "default".to_string());

    let rules = extract_ingress_rules(node);
    if rules.is_empty() {
        return None;
    }

    let mut out = String::new();
    out.push_str("apiVersion: gateway.networking.k8s.io/v1\n");
    out.push_str("kind: HTTPRoute\n");
    out.push_str("metadata:\n");
    out.push_str(&format!("  name: {}\n", name));
    out.push_str(&format!("  namespace: {}\n", ns));
    out.push_str("spec:\n");

    // Collect hostnames
    let hosts: Vec<String> = rules.iter().filter_map(|r| r.host.clone()).collect();
    if !hosts.is_empty() {
        out.push_str("  hostnames:\n");
        for h in hosts {
            out.push_str(&format!("    - \"{}\"\n", h));
        }
    }

    out.push_str("  rules:\n");
    for r in &rules {
        for p in &r.paths {
            out.push_str("    - matches:\n");
            out.push_str("        - path:\n");
            let p_type = if p.path_type.to_lowercase().contains("exact") {
                "Exact"
            } else {
                "PathPrefix"
            };
            out.push_str(&format!("            type: {}\n", p_type));
            out.push_str(&format!("            value: \"{}\"\n", p.path));
            out.push_str("      backendRefs:\n");
            out.push_str(&format!("        - name: {}\n", p.service_name));
            out.push_str(&format!("          port: {}\n", p.service_port));
        }
    }

    let msg = format!(
        "Remediation [{}]: Generated Gateway API HTTPRoute for Ingress '{}'.",
        GATEWAY_API_RULE_ID, name
    );
    native_record_healing_impact(telemetry, &msg);

    Some(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_convert_ingress_to_httproute() {
        let mut telemetry = NativeTelemetry::default();
        let ingress = SemanticNode {
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
                        value: Some("web-ingress".to_string()),
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
                            children: vec![
                                SemanticNode {
                                    key: "host".to_string(),
                                    value: Some("example.com".to_string()),
                                    indent: 6,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                                SemanticNode {
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
                                            children: vec![
                                                SemanticNode {
                                                    key: "path".to_string(),
                                                    value: Some("/api".to_string()),
                                                    indent: 12,
                                                    is_empty_flow: false,
                                                    children: vec![],
                                                    shards: vec![],
                                                },
                                                SemanticNode {
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
                                                        children: vec![
                                                            SemanticNode {
                                                                key: "name".to_string(),
                                                                value: Some("api-svc".to_string()),
                                                                indent: 16,
                                                                is_empty_flow: false,
                                                                children: vec![],
                                                                shards: vec![],
                                                            },
                                                            SemanticNode {
                                                                key: "port".to_string(),
                                                                value: None,
                                                                indent: 16,
                                                                is_empty_flow: false,
                                                                shards: Vec::new(),
                                                                children: vec![SemanticNode {
                                                                    key: "number".to_string(),
                                                                    value: Some("8080".to_string()),
                                                                    indent: 18,
                                                                    is_empty_flow: false,
                                                                    children: vec![],
                                                                    shards: vec![],
                                                                }],
                                                            },
                                                        ],
                                                    }],
                                                },
                                            ],
                                        }],
                                    }],
                                },
                            ],
                        }],
                    }],
                },
            ],
        };

        let route_yaml = convert_ingress_to_httproute(&ingress, &mut telemetry).unwrap();
        assert!(route_yaml.contains("kind: HTTPRoute"));
        assert!(route_yaml.contains("hostnames:"));
        assert!(route_yaml.contains("example.com"));
        assert!(route_yaml.contains("api-svc"));
        assert!(route_yaml.contains("8080"));
    }
}
