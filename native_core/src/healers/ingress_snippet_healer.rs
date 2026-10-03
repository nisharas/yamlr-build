//! Ingress NGINX Configuration Snippet Deprecation Healer (Rule SEC-012).
//!
//! Why: CVE-2021-25742, CVE-2022-4886, and CVE-2023-5044 allow arbitrary command execution
//! and credential exfiltration via ingress-nginx custom snippets. Modern ingress-nginx
//! controllers (v1.9.0+) and managed cloud distributions disable `configuration-snippet`
//! and `server-snippet` by default, causing ingresses with these annotations to fail
//! admission validation or break live routing upon cluster upgrade.
//!
//! This module safely parses snippet directives, decomposing safe patterns (such as CORS
//! headers and rewrite directives) into first-class Ingress annotations, while quarantining
//! complex scripted snippets to prevent production outages.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const INGRESS_SNIPPET_RULE_ID: &str = "SEC-012";

/// Detects deprecated Ingress NGINX configuration snippets and migrates them to native annotations.
pub fn heal_ingress_snippets(
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
        .unwrap_or_else(|| "unnamed-ingress".to_string());

    let mut new_annotations = Vec::new();
    let mut snippet_found = false;
    let mut is_complex = false;

    if let Some(metadata) = manifest.root.find_node_mut("metadata") {
        if let Some(annotations) = metadata.find_node_mut("annotations") {
            let ann_indent = annotations.indent + 2;

            for ann in &mut annotations.children {
                if ann.key == "nginx.ingress.kubernetes.io/configuration-snippet"
                    || ann.key == "nginx.ingress.kubernetes.io/server-snippet"
                {
                    snippet_found = true;
                    let raw_val = ann.value.clone().unwrap_or_default();
                    let clean_val = raw_val.trim().trim_matches('"').trim_matches('\'');

                    // 1. Inspect for CORS headers
                    if clean_val.contains("Access-Control-Allow-Origin") {
                        new_annotations.push((
                            "nginx.ingress.kubernetes.io/enable-cors".to_string(),
                            "\"true\"".to_string(),
                        ));

                        // Extract origin if explicitly specified
                        if let Some(origin) = extract_cors_origin(clean_val) {
                            new_annotations.push((
                                "nginx.ingress.kubernetes.io/cors-allow-origin".to_string(),
                                format!("\"{}\"", origin),
                            ));
                        }
                    }

                    // 2. Inspect for URL rewrite directives: rewrite ^/foo/(.*) /$1 break;
                    if let Some(target) = extract_rewrite_target(clean_val) {
                        new_annotations.push((
                            "nginx.ingress.kubernetes.io/rewrite-target".to_string(),
                            format!("\"{}\"", target),
                        ));
                    }

                    // 3. Inspect for header injection directives (more_set_headers / proxy_set_header)
                    if let Some(header_cfg) = extract_custom_headers_target(clean_val) {
                        new_annotations.push((
                            "nginx.ingress.kubernetes.io/custom-headers".to_string(),
                            format!("\"{}\"", header_cfg),
                        ));
                    }

                    // 4. Detect unconvertible complex Lua, variables, or if-blocks
                    if clean_val.contains("_by_lua")
                        || clean_val.contains("set $")
                        || clean_val.contains("if (")
                    {
                        is_complex = true;
                    }
                }
            }

            // Inject decomposed annotations if not already present
            for (k, v) in new_annotations {
                if annotations.find_node(&k).is_none() {
                    annotations.children.push(SemanticNode {
                        key: k.clone(),
                        value: Some(v.clone()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent: ann_indent,
                        is_empty_flow: false,
                    });
                    let msg = format!(
                        "Remediation [{}]: Decomposed Ingress '{}' snippet into native annotation '{}'.",
                        INGRESS_SNIPPET_RULE_ID, ing_name, k
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }

            // If complex snippet detected, tag with quarantine warning annotation
            if is_complex
                && annotations
                    .find_node("yamlr.dev/snippet-quarantine")
                    .is_none()
            {
                annotations.children.push(SemanticNode {
                    key: "yamlr.dev/snippet-quarantine".to_string(),
                    value: Some("\"manual-migration-required\"".to_string()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: ann_indent,
                    is_empty_flow: false,
                });
                let msg = format!(
                    "Remediation [{}]: Flagged Ingress '{}' with complex configuration snippet for manual migration.",
                    INGRESS_SNIPPET_RULE_ID, ing_name
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            } else if snippet_found && changes.is_empty() {
                // Snippet is present but could not be automatically decomposed
                let msg = format!(
                    "Remediation [{}]: Ingress '{}' uses deprecated configuration-snippet disabled in K8s 1.28+ / Ingress-NGINX v1.9+.",
                    INGRESS_SNIPPET_RULE_ID, ing_name
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    changes
}

fn extract_cors_origin(snippet: &str) -> Option<String> {
    for line in snippet.lines() {
        if line.contains("Access-Control-Allow-Origin") {
            let parts: Vec<&str> = line.split_whitespace().collect();
            for (idx, p) in parts.iter().enumerate() {
                if p.contains("Access-Control-Allow-Origin") && idx + 1 < parts.len() {
                    let origin = parts[idx + 1]
                        .trim_matches(';')
                        .trim_matches('\'')
                        .trim_matches('"');
                    return Some(origin.to_string());
                }
            }
        }
    }
    None
}

fn extract_rewrite_target(snippet: &str) -> Option<String> {
    for line in snippet.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("rewrite ") {
            let parts: Vec<&str> = trimmed.split_whitespace().collect();
            if parts.len() >= 3 {
                let target = parts[2].trim_matches(';');
                return Some(target.to_string());
            }
        }
    }
    None
}

fn extract_custom_headers_target(snippet: &str) -> Option<String> {
    for line in snippet.lines() {
        let trimmed = line.trim();
        if trimmed.contains("proxy_set_header") || trimmed.contains("more_set_headers") {
            // Suggest or link to default/custom-headers ConfigMap buffer
            return Some("ingress-nginx/custom-headers".to_string());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::SemanticNode;

    #[test]
    fn test_decompose_cors_snippet() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode { key: "kind".into(), value: Some("Ingress".into()), children: vec![], shards: vec![], indent: 0, is_empty_flow: false },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![
                            SemanticNode { key: "name".into(), value: Some("web-ing".into()), children: vec![], shards: vec![], indent: 2, is_empty_flow: false },
                            SemanticNode {
                                key: "annotations".into(),
                                value: None,
                                children: vec![
                                    SemanticNode {
                                        key: "nginx.ingress.kubernetes.io/configuration-snippet".into(),
                                        value: Some("more_set_headers 'Access-Control-Allow-Origin: https://app.example.com';".into()),
                                        children: vec![],
                                        shards: vec![],
                                        indent: 4,
                                        is_empty_flow: false,
                                    }
                                ],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            }
                        ],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    }
                ],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            indent_step: 2,
            integrity_violations: vec![],
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_ingress_snippets(&mut manifest, &mut telemetry);
        assert!(!changes.is_empty());

        let meta = manifest.root.find_node("metadata").unwrap();
        let ann = meta.find_node("annotations").unwrap();
        assert_eq!(
            ann.find_value("nginx.ingress.kubernetes.io/enable-cors"),
            Some("\"true\"".to_string())
        );
    }

    #[test]
    fn test_decompose_rewrite_snippet() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Ingress".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "name".into(),
                                value: Some("rewrite-ing".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "annotations".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "nginx.ingress.kubernetes.io/configuration-snippet".into(),
                                    value: Some("rewrite ^/api/(.*) /$1 break;".into()),
                                    children: vec![],
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

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_ingress_snippets(&mut manifest, &mut telemetry);
        assert!(!changes.is_empty());

        let meta = manifest.root.find_node("metadata").unwrap();
        let ann = meta.find_node("annotations").unwrap();
        assert_eq!(
            ann.find_value("nginx.ingress.kubernetes.io/rewrite-target"),
            Some("\"/$1\"".to_string())
        );
    }

    #[test]
    fn test_quarantine_complex_lua_snippet() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Ingress".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "name".into(),
                                value: Some("lua-ing".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "annotations".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "nginx.ingress.kubernetes.io/configuration-snippet".into(),
                                    value: Some("access_by_lua_block { check_auth() }".into()),
                                    children: vec![],
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

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_ingress_snippets(&mut manifest, &mut telemetry);
        assert!(!changes.is_empty());

        let meta = manifest.root.find_node("metadata").unwrap();
        let ann = meta.find_node("annotations").unwrap();
        assert_eq!(
            ann.find_value("yamlr.dev/snippet-quarantine"),
            Some("\"manual-migration-required\"".to_string())
        );
    }

    #[test]
    fn test_decompose_header_injection_snippet() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Ingress".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "name".into(),
                                value: Some("header-ing".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "annotations".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "nginx.ingress.kubernetes.io/configuration-snippet".into(),
                                    value: Some(
                                        "more_set_headers 'X-Frame-Options: SAMEORIGIN';".into(),
                                    ),
                                    children: vec![],
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

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_ingress_snippets(&mut manifest, &mut telemetry);
        assert!(!changes.is_empty());

        let meta = manifest.root.find_node("metadata").unwrap();
        let ann = meta.find_node("annotations").unwrap();
        assert_eq!(
            ann.find_value("nginx.ingress.kubernetes.io/custom-headers"),
            Some("\"ingress-nginx/custom-headers\"".to_string())
        );
    }
}
