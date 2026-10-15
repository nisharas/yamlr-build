//! Ingress Path Shadowing & Specificity Ordering Healer (Rule NET-004).
//!
//! Why: In Kubernetes, Ingress controllers evaluate paths based on order and specificity.
//! If an Ingress defines a broad prefix like `/api` (`pathType: Prefix`) BEFORE a more specific
//! sub-path like `/api/v1/checkout`, the parent prefix shadows the sub-path. Traffic meant
//! for checkout is swallowed by the `/api` service, returning silent 404 Not Found errors.
//!
//! Yamlr calculates prefix specificity and re-orders path rules so that more specific sub-paths
//! always precede parent wildcard prefixes, preventing routing blackholes.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const INGRESS_SHADOW_RULE_ID: &str = "NET-008";

/// Primary entrypoint: Detects and fixes shadowed Ingress paths by ordering by specificity.
pub fn heal_ingress_shadowing(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Ingress" {
        return changes;
    }

    let ing_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "ingress".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        for paths in spec.find_nodes_by_key_recursive_mut("paths") {
            // Trap 58 / Rule ING-003: Prepend mandatory leading slash to relative Ingress paths
            for path_item in &mut paths.children {
                if let Some(path_node) = path_item.find_node_mut("path") {
                    if let Some(val) = &path_node.value {
                        let trimmed = val.trim();
                        let clean = trimmed.trim_matches(|c| c == '\'' || c == '"');
                        if !clean.is_empty() && !clean.starts_with('/') {
                            let fixed_path = format!("/{}", clean);
                            let old_val = val.clone();
                            path_node.value = Some(fixed_path.clone());
                            for s in &mut path_node.shards {
                                s.value = Some(fixed_path.clone());
                            }
                            let msg = format!(
                                "Remediation [ING-003]: Prepended mandatory leading slash to Ingress '{}' path '{}' -> '{}'.",
                                ing_name, old_val, fixed_path
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }

                // Trap 68 / Rule ING-004: Ingress backend service port mutual exclusivity (number vs name)
                // In Kubernetes networking.k8s.io/v1 IngressBackend, ServiceBackendPort is a oneOf union:
                // either `number: <int>` OR `name: <string>`. If both are specified, kube-apiserver fails validation.
                if let Some(backend) = path_item.find_node_mut("backend") {
                    if let Some(svc) = backend.find_node_mut("service") {
                        if let Some(port) = svc.find_node_mut("port") {
                            let has_number = port.find_node("number").is_some();
                            let has_name = port.find_node("name").is_some();
                            if has_number && has_name {
                                let pruned_name = port.find_value("name").unwrap_or_default();
                                port.children.retain(|c| c.key != "name");
                                port.shards.retain(|s| s.key != "name");
                                let msg = format!(
                                    "Remediation [ING-004]: Resolved Ingress '{}' backend port mutual exclusivity conflict: retained 'number' and pruned redundant 'name: {}'.",
                                    ing_name, pruned_name
                                );
                                native_record_healing_impact(telemetry, &msg);
                                changes.push(msg);
                            }
                        }
                    }
                }
            }

            if paths.children.len() <= 1 {
                continue;
            }

            // Check if paths are currently ordered from most specific to least specific
            let mut needs_reorder = false;
            let mut shadow_pair = None;

            for i in 0..paths.children.len() - 1 {
                let curr_spec = get_path_specificity(&paths.children[i]);
                let next_spec = get_path_specificity(&paths.children[i + 1]);

                // If a less specific path precedes a more specific path, it's shadowing
                if curr_spec < next_spec {
                    needs_reorder = true;
                    let p1 = paths.children[i].find_value("path").unwrap_or_default();
                    let p2 = paths.children[i + 1].find_value("path").unwrap_or_default();
                    shadow_pair = Some((p1, p2));
                    break;
                }
            }

            if needs_reorder {
                // Sort paths descending by specificity (highest specificity first)
                paths.children.sort_by(|a, b| {
                    let spec_a = get_path_specificity(a);
                    let spec_b = get_path_specificity(b);
                    spec_b.cmp(&spec_a)
                });

                let (broad_p, specific_p) = shadow_pair.unwrap_or_default();
                let msg = format!(
                    "Remediation [{}]: Reordered Ingress paths on '{}' to prevent path shadowing: placed specific sub-path '{}' before parent prefix '{}'.",
                    INGRESS_SHADOW_RULE_ID, ing_name, specific_p, broad_p
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    changes
}

/// Calculates a comparable specificity score for an Ingress path item.
/// Higher score = more specific (must be evaluated earlier).
fn get_path_specificity(path_node: &SemanticNode) -> (u8, usize, usize) {
    let raw_path = path_node.find_value("path").unwrap_or_default();
    let path_type = path_node
        .find_value("pathType")
        .unwrap_or_else(|| "Prefix".to_string());

    let clean_path = raw_path.trim().trim_matches('"').trim_matches('\'');

    // 1. PathType precedence: Exact (2) > Prefix (1) > ImplementationSpecific (0)
    let type_score = match path_type.as_str() {
        "Exact" => 2,
        "Prefix" => 1,
        _ => 0,
    };

    // 2. Segment depth: number of path segments (e.g., /api/v1/checkout has depth 3)
    let segments = clean_path.split('/').filter(|s| !s.is_empty()).count();

    // 3. String length (longer path is more specific)
    let len = clean_path.len();

    (type_score, segments, len)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_ingress_with_paths(paths_data: Vec<(&str, &str)>) -> SemanticManifest {
        let path_nodes: Vec<SemanticNode> = paths_data
            .into_iter()
            .map(|(path, path_type)| SemanticNode {
                key: "-".to_string(),
                value: None,
                indent: 8,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "path".to_string(),
                        value: Some(path.to_string()),
                        indent: 10,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "pathType".to_string(),
                        value: Some(path_type.to_string()),
                        indent: 10,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "backend".to_string(),
                        value: None,
                        indent: 10,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "service".to_string(),
                            value: None,
                            indent: 12,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "name".to_string(),
                                value: Some(format!("svc-{}", path.replace('/', "-"))),
                                indent: 14,
                                is_empty_flow: false,
                                children: vec![],
                                shards: vec![],
                            }],
                        }],
                    },
                ],
            })
            .collect();

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
                            value: Some("public-api-gateway".to_string()),
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
                                        value: Some("api.example.com".to_string()),
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
                                            children: path_nodes,
                                        }],
                                    },
                                ],
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
    fn test_reorder_shadowed_subpath() {
        let mut telemetry = NativeTelemetry::default();
        // /api precedes /api/v1/checkout -> shadowing bug
        let mut manifest =
            create_ingress_with_paths(vec![("/api", "Prefix"), ("/api/v1/checkout", "Prefix")]);

        let changes = heal_ingress_shadowing(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Reordered Ingress paths"));

        let spec = manifest.root.find_node("spec").unwrap();
        let rules = spec.find_node("rules").unwrap();
        let http = rules.children[0].find_node("http").unwrap();
        let paths = http.find_node("paths").unwrap();

        // /api/v1/checkout should now be first!
        assert_eq!(
            paths.children[0].find_value("path"),
            Some("/api/v1/checkout".to_string())
        );
        assert_eq!(
            paths.children[1].find_value("path"),
            Some("/api".to_string())
        );
    }

    #[test]
    fn test_exact_path_precedes_prefix() {
        let mut telemetry = NativeTelemetry::default();
        // /login Prefix precedes /login Exact -> shadowing bug
        let mut manifest =
            create_ingress_with_paths(vec![("/login", "Prefix"), ("/login", "Exact")]);

        let changes = heal_ingress_shadowing(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);

        let spec = manifest.root.find_node("spec").unwrap();
        let rules = spec.find_node("rules").unwrap();
        let http = rules.children[0].find_node("http").unwrap();
        let paths = http.find_node("paths").unwrap();

        assert_eq!(
            paths.children[0].find_value("pathType"),
            Some("Exact".to_string())
        );
        assert_eq!(
            paths.children[1].find_value("pathType"),
            Some("Prefix".to_string())
        );
    }

    #[test]
    fn test_already_ordered_paths_idempotent() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest =
            create_ingress_with_paths(vec![("/api/v1/checkout", "Prefix"), ("/api", "Prefix")]);

        let changes = heal_ingress_shadowing(&mut manifest, &mut telemetry);
        assert!(changes.is_empty());
    }

    #[test]
    fn test_ingress_path_leading_slash() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest =
            create_ingress_with_paths(vec![("api/v1", "Prefix")]);

        let changes = heal_ingress_shadowing(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("[ING-003]"));

        let spec = manifest.root.find_node("spec").unwrap();
        let rules = spec.find_node("rules").unwrap();
        let http = rules.children[0].find_node("http").unwrap();
        let paths = http.find_node("paths").unwrap();
        assert_eq!(paths.children[0].find_value("path"), Some("/api/v1".to_string()));
    }

    #[test]
    fn test_ingress_backend_port_number_name_conflict() {
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
                            value: Some("api-gw".to_string()),
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
                                                    key: "pathType".to_string(),
                                                    value: Some("Prefix".to_string()),
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
                                                                children: vec![
                                                                    SemanticNode {
                                                                        key: "number".to_string(),
                                                                        value: Some("8080".to_string()),
                                                                        indent: 18,
                                                                        is_empty_flow: false,
                                                                        children: vec![],
                                                                        shards: vec![],
                                                                    },
                                                                    SemanticNode {
                                                                        key: "name".to_string(),
                                                                        value: Some("http".to_string()), // Conflict!
                                                                        indent: 18,
                                                                        is_empty_flow: false,
                                                                        children: vec![],
                                                                        shards: vec![],
                                                                    },
                                                                ],
                                                            },
                                                        ],
                                                    }],
                                                },
                                            ],
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

        let changes = heal_ingress_shadowing(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("ING-004"));

        let spec = manifest.root.find_node("spec").unwrap();
        let rules = spec.find_node("rules").unwrap();
        let http = rules.children[0].find_node("http").unwrap();
        let paths = http.find_node("paths").unwrap();
        let backend = paths.children[0].find_node("backend").unwrap();
        let service = backend.find_node("service").unwrap();
        let port = service.find_node("port").unwrap();
        assert_eq!(port.find_value("number"), Some("8080".to_string()));
        assert!(port.find_node("name").is_none());
    }
}
