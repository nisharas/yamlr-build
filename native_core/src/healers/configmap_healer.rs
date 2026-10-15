//! ConfigMap Reference Alignment Healer (Rule REF-002).
//!
//! Why: Misspelled ConfigMap references in `env[].valueFrom.configMapKeyRef`, `envFrom[].configMapRef`,
//! and `volumes[].configMap.name` crash container startup with `CreateContainerConfigError`.
//!
//! This module searches the AST for ConfigMap references and fuzzy repairs names against known ConfigMaps.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const CONFIGMAP_REF_RULE_ID: &str = "REF-002";
pub const CM_SIMILARITY_THRESHOLD: f64 = 0.70;

/// Recursively aligns ConfigMap references in a node tree.
fn align_configmaps_recursive(
    node: &mut SemanticNode,
    ns: &str,
    cms: &[&NativeIdentity],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "data" || node.key == "stringData" || node.key == "binaryData" {
        return;
    }

    let key_lower = node.key.to_lowercase();

    // 1. env[].valueFrom.configMapKeyRef or envFrom[].configMapRef
    if key_lower == "configmapref" || key_lower == "configmapkeyref" {
        if let Some(name_node) = node.find_node_mut("name") {
            let current = name_node.value.clone().unwrap_or_default();
            let clean = current.trim().trim_matches('"').trim_matches('\'');
            if !clean.is_empty() && !cms.iter().any(|c| c.name == clean) && !cms.is_empty() {
                let mut best_target = None;
                let mut best_ratio = 0.0;
                for cm in cms {
                    let is_kustomize_match = cm.name.len() == clean.len() + 11
                        && cm.name.starts_with(clean)
                        && cm.name.chars().nth(clean.len()) == Some('-')
                        && cm.name[clean.len() + 1..]
                            .chars()
                            .all(|c| c.is_ascii_alphanumeric());

                    if is_kustomize_match {
                        best_target = Some(cm.name.clone());
                        best_ratio = 1.0;
                        break;
                    }

                    let ratio = crate::healers::selector_healer::similarity_ratio(clean, &cm.name);
                    if ratio >= CM_SIMILARITY_THRESHOLD && ratio > best_ratio {
                        best_ratio = ratio;
                        best_target = Some(cm.name.clone());
                    }
                }

                if let Some(target) = best_target {
                    name_node.value = Some(target.clone());
                    for s in &mut name_node.shards {
                        s.value = Some(target.clone());
                    }
                    let msg = format!(
                        "Remediation [{}]: Aligned ConfigMap reference '{}' -> '{}' in namespace '{}' (similarity: {:.2}).",
                        CONFIGMAP_REF_RULE_ID, clean, target, ns, best_ratio
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    // 2. volumes[].configMap.name
    if key_lower == "configmap" {
        if let Some(name_node) = node.find_node_mut("name") {
            let current = name_node.value.clone().unwrap_or_default();
            let clean = current.trim().trim_matches('"').trim_matches('\'');
            if !clean.is_empty() && !cms.iter().any(|c| c.name == clean) && !cms.is_empty() {
                let mut best_target = None;
                let mut best_ratio = 0.0;
                for cm in cms {
                    let is_kustomize_match = cm.name.len() == clean.len() + 11
                        && cm.name.starts_with(clean)
                        && cm.name.chars().nth(clean.len()) == Some('-')
                        && cm.name[clean.len() + 1..]
                            .chars()
                            .all(|c| c.is_ascii_alphanumeric());

                    if is_kustomize_match {
                        best_target = Some(cm.name.clone());
                        best_ratio = 1.0;
                        break;
                    }

                    let ratio = crate::healers::selector_healer::similarity_ratio(clean, &cm.name);
                    if ratio >= CM_SIMILARITY_THRESHOLD && ratio > best_ratio {
                        best_ratio = ratio;
                        best_target = Some(cm.name.clone());
                    }
                }

                if let Some(target) = best_target {
                    name_node.value = Some(target.clone());
                    for s in &mut name_node.shards {
                        s.value = Some(target.clone());
                    }
                    let msg = format!(
                        "Remediation [{}]: Aligned volume ConfigMap name '{}' -> '{}' in namespace '{}' (similarity: {:.2}).",
                        CONFIGMAP_REF_RULE_ID, clean, target, ns, best_ratio
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    for child in &mut node.children {
        align_configmaps_recursive(child, ns, cms, telemetry, changes);
    }
}

/// Primary Entrypoint: Aligns all broken ConfigMap references in a manifest against known identities.
pub fn heal_configmap_references(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let effective_ns = if ns.is_empty() { "default" } else { &ns };
    let cms: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| {
            let target_ns = if id.namespace.is_empty() { "default" } else { &id.namespace };
            id.kind == "ConfigMap" && target_ns == effective_ns
        })
        .collect();

    align_configmaps_recursive(&mut manifest.root, &ns, &cms, telemetry, &mut changes);
    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_align_volume_configmap_typo() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![SemanticNode {
                    key: "configMap".into(),
                    value: None,
                    children: vec![SemanticNode {
                        key: "name".into(),
                        value: Some("app-settngs".into()),
                        children: vec![],
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
            indent_step: 2,
            integrity_violations: vec![],
        };

        let target_cm = NativeIdentity {
            kind: "ConfigMap".into(),
            name: "app-settings".into(),
            namespace: "default".into(),
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_configmap_references(&mut manifest, &[target_cm], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let cm_node = manifest.root.find_node("configMap").unwrap();
        assert_eq!(cm_node.find_value("name"), Some("app-settings".to_string()));
    }
}
