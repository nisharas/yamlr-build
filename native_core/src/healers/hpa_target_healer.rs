//! HorizontalPodAutoscaler Target Reference Healer (Rule AUT-001).
//!
//! Why: In an HPA (`HorizontalPodAutoscaler`), typos in `spec.scaleTargetRef.name` or deprecated
//! `apiVersion` (e.g. `extensions/v1beta1` instead of `apps/v1`) prevent HPA controller discovery,
//! leaving production workloads unable to scale out during traffic spikes.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const HPA_TARGET_RULE_ID: &str = "AUT-001";
pub const HPA_SIMILARITY_THRESHOLD: f64 = 0.70;

/// Aligns HPA scaleTargetRef apiVersion and workload name against known identities.
pub fn heal_hpa_target_refs(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "HorizontalPodAutoscaler" {
        return changes;
    }

    let hpa_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-hpa".to_string());

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(target_ref) = spec.find_node_mut("scaleTargetRef") {
            // 1. Upgrade deprecated apiVersion
            if let Some(api_node) = target_ref.find_node_mut("apiVersion") {
                let current_api = api_node.value.clone().unwrap_or_default();
                let clean_api = current_api.trim().trim_matches('"').trim_matches('\'');
                if clean_api == "extensions/v1beta1"
                    || clean_api == "apps/v1beta1"
                    || clean_api == "apps/v1beta2"
                {
                    api_node.value = Some("apps/v1".to_string());
                    for s in &mut api_node.shards {
                        s.value = Some("apps/v1".to_string());
                    }
                    let msg = format!(
                        "Remediation [{}]: Upgraded HPA '{}' scaleTargetRef.apiVersion '{}' -> 'apps/v1'.",
                        HPA_TARGET_RULE_ID, hpa_name, clean_api
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }

            // 2. Fuzzy match target workload name
            let target_kind = target_ref
                .find_value("kind")
                .unwrap_or_else(|| "Deployment".to_string());
            let current_name = target_ref.find_value("name").unwrap_or_default();
            let clean_name = current_name.trim().trim_matches('"').trim_matches('\'');

            let workloads: Vec<&NativeIdentity> = identities
                .iter()
                .filter(|id| {
                    id.kind == target_kind
                        && (id.namespace == ns
                            || id.namespace.is_empty()
                            || id.namespace == "default")
                })
                .collect();

            if !clean_name.is_empty()
                && !workloads.iter().any(|w| w.name == clean_name)
                && !workloads.is_empty()
            {
                let mut best_target = None;
                let mut best_ratio = 0.0;
                for w in workloads {
                    let ratio =
                        crate::healers::selector_healer::similarity_ratio(clean_name, &w.name);
                    if ratio >= HPA_SIMILARITY_THRESHOLD && ratio > best_ratio {
                        best_ratio = ratio;
                        best_target = Some(w.name.clone());
                    }
                }

                if let Some(target) = best_target {
                    if let Some(name_node) = target_ref.find_node_mut("name") {
                        name_node.value = Some(target.clone());
                        for s in &mut name_node.shards {
                            s.value = Some(target.clone());
                        }
                        let msg = format!(
                            "Remediation [{}]: Aligned HPA '{}' scaleTargetRef name '{}' -> '{}' ({}) (similarity: {:.2}).",
                            HPA_TARGET_RULE_ID, hpa_name, clean_name, target, target_kind, best_ratio
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }

        // Trap 67 / Rule AUT-002: Inverted replica bounds (minReplicas > maxReplicas)
        let min_rep = spec
            .find_node("minReplicas")
            .and_then(|n| n.value.as_ref())
            .and_then(|v| v.trim_matches(|c| c == '\'' || c == '"').parse::<i32>().ok());
        let max_rep = spec
            .find_node("maxReplicas")
            .and_then(|n| n.value.as_ref())
            .and_then(|v| v.trim_matches(|c| c == '\'' || c == '"').parse::<i32>().ok());

        if let (Some(min), Some(max)) = (min_rep, max_rep) {
            if min > max {
                // Align maxReplicas = minReplicas so that maxReplicas >= minReplicas invariant is satisfied
                if let Some(max_node) = spec.find_node_mut("maxReplicas") {
                    let old_val = max.to_string();
                    let new_val = min.to_string();
                    max_node.value = Some(new_val.clone());
                    for s in &mut max_node.shards {
                        s.value = Some(new_val.clone());
                    }
                    let msg = format!(
                        "Remediation [AUT-002]: Corrected inverted HPA '{}' replicas: raised maxReplicas {} -> {} (must be >= minReplicas {}).",
                        hpa_name, old_val, new_val, min
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
    use crate::models::SemanticNode;

    #[test]
    fn test_hpa_api_and_target_alignment() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("HorizontalPodAutoscaler".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "scaleTargetRef".into(),
                            value: None,
                            children: vec![
                                SemanticNode {
                                    key: "apiVersion".into(),
                                    value: Some("extensions/v1beta1".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                },
                                SemanticNode {
                                    key: "kind".into(),
                                    value: Some("Deployment".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                },
                                SemanticNode {
                                    key: "name".into(),
                                    value: Some("web-ap".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                },
                            ],
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

        let target_dep = NativeIdentity {
            kind: "Deployment".into(),
            name: "web-api".into(),
            namespace: "default".into(),
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_hpa_target_refs(&mut manifest, &[target_dep], &mut telemetry);
        assert_eq!(changes.len(), 2);
        let spec = manifest.root.find_node("spec").unwrap();
        let ref_node = spec.find_node("scaleTargetRef").unwrap();
        assert_eq!(
            ref_node.find_value("apiVersion"),
            Some("apps/v1".to_string())
        );
        assert_eq!(ref_node.find_value("name"), Some("web-api".to_string()));
    }

    #[test]
    fn test_hpa_inverted_replicas() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("HorizontalPodAutoscaler".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "name".into(),
                            value: Some("api-hpa".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "minReplicas".into(),
                                value: Some("5".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "maxReplicas".into(),
                                value: Some("2".into()), // Inverted! min (5) > max (2)
                                children: vec![],
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
        let changes = heal_hpa_target_refs(&mut manifest, &[], &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("AUT-002"));

        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(spec.find_value("maxReplicas"), Some("5".to_string()));
    }
}
