//! Annotation Contract & Cloud-Agnostic Metadata Healers (Rule ANN-001 / Trap 48).
//!
//! Why: In Kubernetes `metadata.annotations`, all keys and values must conform to strict string contracts.
//! A frequent production incident occurs with boolean annotations such as Cluster Autoscaler's
//! `cluster-autoscaler.kubernetes.io/safe-to-evict` or `safe-to-evict`:
//!
//! 1. Authors frequently write unquoted boolean literals (`safe-to-evict: true` or `false`).
//!    In strict Kubernetes OpenAPI v3 admission, annotations must be a map of string to string
//!    (`map[string]string`). An unquoted boolean scalar causes immediate apiserver admission rejection:
//!    `Invalid value: true: spec.template.metadata.annotations: Invalid value: "boolean": expected string`.
//!
//! 2. Authors frequently write capitalized strings (`"True"` or `"False"`). The Kubernetes Cluster
//!    Autoscaler strictly parses `safe-to-evict` using `strconv.ParseBool(val)`. While Go `strconv.ParseBool`
//!    accepts "true" or "1", many third-party GitOps controllers, policy validators (OPA/Kyverno), and
//!    autoscaler implementations require lowercase `"true"` or `"false"`.
//!
//! Yamlr normalizes boolean annotations into canonical quoted lowercase strings (`"true"` / `"false"`),
//! cloud-agnostically across all Kubernetes workloads and templates.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_ANN_001: &str = "ANN-001";

/// Returns true if the annotation key represents a known boolean-contract annotation.
pub fn is_boolean_annotation_key(key: &str) -> bool {
    let lower = key.to_lowercase();
    lower == "cluster-autoscaler.kubernetes.io/safe-to-evict"
        || lower.ends_with("/safe-to-evict")
        || lower == "safe-to-evict"
        || lower == "karpenter.sh/do-not-disrupt"
}

/// Recursively scans for `annotations:` blocks in `metadata` and normalizes boolean values.
fn heal_annotation_booleans_recursive(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "annotations" {
        for ann_child in &mut node.children {
            if is_boolean_annotation_key(&ann_child.key) {
                if let Some(val) = &ann_child.value {
                    let trimmed = val.trim();
                    let clean = trimmed.trim_matches(|c| c == '\'' || c == '"').trim();
                    let clean_lower = clean.to_lowercase();

                    if clean_lower == "true" || clean_lower == "yes" || clean_lower == "1" {
                        let canonical = "\"true\"".to_string();
                        if *val != canonical {
                            let old_val = val.clone();
                            ann_child.value = Some(canonical.clone());
                            for s in &mut ann_child.shards {
                                s.value = Some(canonical.clone());
                            }
                            let msg = format!(
                                "Remediation [{}]: Normalized boolean annotation '{}': {} -> \"true\" to satisfy string contract.",
                                RULE_ANN_001, ann_child.key, old_val
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    } else if clean_lower == "false" || clean_lower == "no" || clean_lower == "0" {
                        let canonical = "\"false\"".to_string();
                        if *val != canonical {
                            let old_val = val.clone();
                            ann_child.value = Some(canonical.clone());
                            for s in &mut ann_child.shards {
                                s.value = Some(canonical.clone());
                            }
                            let msg = format!(
                                "Remediation [{}]: Normalized boolean annotation '{}': {} -> \"false\" to satisfy string contract.",
                                RULE_ANN_001, ann_child.key, old_val
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }
        }
    }

    for child in &mut node.children {
        heal_annotation_booleans_recursive(child, telemetry, changes);
    }
}

/// Primary Entrypoint: Heals boolean contract violations in annotations across a manifest.
pub fn heal_annotation_contracts(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    // CustomResourceDefinition schema objects contain OpenAPI v3 definitions, not runtime metadata annotations
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    heal_annotation_booleans_recursive(&mut manifest.root, telemetry, &mut changes);

    // Trap 52 / Rule ING-002: Promote deprecated kubernetes.io/ingress.class annotation to spec.ingressClassName
    let ing_changes = heal_ingress_class_name(manifest, telemetry);
    changes.extend(ing_changes);

    changes
}

pub const RULE_ING_002: &str = "ING-002";

/// Rule ING-002 (Trap 52): Promotes deprecated `kubernetes.io/ingress.class` annotation to `spec.ingressClassName`.
///
/// Why: Kubernetes 1.18+ deprecated `kubernetes.io/ingress.class` in favor of the first-class `spec.ingressClassName`.
/// In Kubernetes 1.22+ (`networking.k8s.io/v1`), modern Ingress controllers (NGINX, Traefik, AWS ALB) prioritize
/// or require `spec.ingressClassName`. Manifests that only specify the legacy annotation fail to bind or trigger
/// admission deprecation warnings.
///
/// Zero-assumption: Promoting the annotation value to `spec.ingressClassName` (if not already set) satisfies
/// modern admission schemas deterministically while maintaining full cluster compatibility.
pub fn heal_ingress_class_name(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Ingress" {
        return changes;
    }

    let ingress_class_val = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_node("annotations"))
        .and_then(|a| a.find_value("kubernetes.io/ingress.class"))
        .map(|v| v.trim().trim_matches(|c| c == '\'' || c == '"').to_string());

    if let Some(class_name) = ingress_class_val {
        if !class_name.is_empty() {
            if let Some(spec) = manifest.root.find_node_mut("spec") {
                if spec.find_node("ingressClassName").is_none() {
                    let s_indent = spec.indent;
                    spec.children.insert(
                        0,
                        SemanticNode {
                            key: "ingressClassName".to_string(),
                            value: Some(class_name.clone()),
                            indent: s_indent + 2,
                            is_empty_flow: false,
                            children: Vec::new(),
                            shards: Vec::new(),
                        },
                    );
                }
            }

            // Prune deprecated annotation from metadata.annotations
            if let Some(metadata) = manifest.root.find_node_mut("metadata") {
                if let Some(annotations) = metadata.find_node_mut("annotations") {
                    annotations.children.retain(|c| c.key != "kubernetes.io/ingress.class");
                }
            }

            let ing_name = manifest
                .root
                .find_node("metadata")
                .and_then(|m| m.find_value("name"))
                .unwrap_or_else(|| "unnamed-ingress".to_string());

            let msg = format!(
                "Remediation [{}]: Promoted legacy 'kubernetes.io/ingress.class' annotation to 'spec.ingressClassName: {}' on Ingress '{}'.",
                RULE_ING_002, class_name, ing_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heal_unquoted_boolean_annotation() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".to_string(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "kind".to_string(),
                        value: Some("Deployment".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "metadata".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "annotations".to_string(),
                                value: None,
                                indent: 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![
                                    SemanticNode {
                                        key: "cluster-autoscaler.kubernetes.io/safe-to-evict".to_string(),
                                        value: Some("true".to_string()), // unquoted boolean literal in YAML
                                        indent: 4,
                                        is_empty_flow: false,
                                        children: Vec::new(),
                                        shards: Vec::new(),
                                    },
                                    SemanticNode {
                                        key: "karpenter.sh/do-not-disrupt".to_string(),
                                        value: Some("\"True\"".to_string()), // capitalized string
                                        indent: 4,
                                        is_empty_flow: false,
                                        children: Vec::new(),
                                        shards: Vec::new(),
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_annotation_contracts(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 2);

        let annotations = manifest
            .root
            .find_node("metadata")
            .unwrap()
            .find_node("annotations")
            .unwrap();

        assert_eq!(
            annotations.find_value("cluster-autoscaler.kubernetes.io/safe-to-evict"),
            Some("\"true\"".to_string())
        );
        assert_eq!(
            annotations.find_value("karpenter.sh/do-not-disrupt"),
            Some("\"true\"".to_string())
        );
    }

    #[test]
    fn test_heal_ingress_class_name_promotion() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".to_string(),
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
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "metadata".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "name".to_string(),
                                value: Some("public-gateway".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                            SemanticNode {
                                key: "annotations".to_string(),
                                value: None,
                                indent: 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![
                                    SemanticNode {
                                        key: "kubernetes.io/ingress.class".to_string(),
                                        value: Some("\"nginx\"".to_string()),
                                        indent: 4,
                                        is_empty_flow: false,
                                        children: Vec::new(),
                                        shards: Vec::new(),
                                    },
                                ],
                            },
                        ],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_annotation_contracts(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("[ING-002]"));

        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(spec.find_value("ingressClassName"), Some("nginx".to_string()));
    }
}

