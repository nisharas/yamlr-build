//! PersistentVolumeClaim Reference Alignment Healer (Rule REF-003).
//!
//! Why: In Kubernetes pod specs, typos in `volumes[].persistentVolumeClaim.claimName`
//! prevent the volume from mounting, leaving pods stuck in `ContainerCreating` indefinitely.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const PVC_REF_RULE_ID: &str = "REF-003";
pub const PVC_SIMILARITY_THRESHOLD: f64 = 0.70;

/// Recursively aligns PVC claimName references in an AST node.
fn align_pvc_refs_recursive(
    node: &mut SemanticNode,
    ns: &str,
    pvcs: &[&NativeIdentity],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let key_lower = node.key.to_lowercase();
    if key_lower == "persistentvolumeclaim" {
        if let Some(claim_node) = node.find_node_mut("claimName") {
            let current = claim_node.value.clone().unwrap_or_default();
            let clean = current.trim().trim_matches('"').trim_matches('\'');

            if !clean.is_empty() && !pvcs.iter().any(|p| p.name == clean) && !pvcs.is_empty() {
                let mut best_target = None;
                let mut best_ratio = 0.0;
                for p in pvcs {
                    let ratio = crate::healers::selector_healer::similarity_ratio(clean, &p.name);
                    if ratio >= PVC_SIMILARITY_THRESHOLD && ratio > best_ratio {
                        best_ratio = ratio;
                        best_target = Some(p.name.clone());
                    }
                }

                if let Some(target) = best_target {
                    claim_node.value = Some(target.clone());
                    for s in &mut claim_node.shards {
                        s.value = Some(target.clone());
                    }
                    let msg = format!(
                        "Remediation [{}]: Aligned PersistentVolumeClaim claimName '{}' -> '{}' in namespace '{}' (similarity: {:.2}).",
                        PVC_REF_RULE_ID, clean, target, ns, best_ratio
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    for child in &mut node.children {
        align_pvc_refs_recursive(child, ns, pvcs, telemetry, changes);
    }
}

/// Primary Entrypoint: Aligns all broken PersistentVolumeClaim references in a manifest against known identities.
pub fn heal_pvc_references(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let pvcs: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| {
            id.kind == "PersistentVolumeClaim"
                && (id.namespace == ns || id.namespace.is_empty() || id.namespace == "default")
        })
        .collect();

    align_pvc_refs_recursive(&mut manifest.root, &ns, &pvcs, telemetry, &mut changes);
    changes
}

/// Entrypoint for StorageClass volumeBindingMode Alignment (Rule STR-004).
///
/// Multi-zone clusters require `volumeBindingMode: WaitForFirstConsumer` to ensure
/// PVs are dynamically provisioned in the availability zone where the requesting pod is scheduled.
pub fn heal_storage_class_binding_modes(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    let is_storage_class = manifest
        .root
        .find_value("kind")
        .map(|k| k == "StorageClass")
        .unwrap_or(false);

    if !is_storage_class {
        return changes;
    }

    if let Some(mode_node) = manifest.root.find_node_mut("volumeBindingMode") {
        if let Some(val) = &mode_node.value {
            if val.eq_ignore_ascii_case("immediate") {
                mode_node.value = Some("WaitForFirstConsumer".to_string());
                for s in &mut mode_node.shards {
                    s.value = Some("WaitForFirstConsumer".to_string());
                }
                let msg = "Remediation [STR-004]: Aligned StorageClass volumeBindingMode from 'Immediate' -> 'WaitForFirstConsumer' for multi-zone topology scheduling safety.".to_string();
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_align_pvc_claim_name_typo() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![SemanticNode {
                    key: "persistentVolumeClaim".into(),
                    value: None,
                    children: vec![SemanticNode {
                        key: "claimName".into(),
                        value: Some("data-volum".into()),
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

        let target_pvc = NativeIdentity {
            kind: "PersistentVolumeClaim".into(),
            name: "data-volume".into(),
            namespace: "default".into(),
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_pvc_references(&mut manifest, &[target_pvc], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let pvc_node = manifest.root.find_node("persistentVolumeClaim").unwrap();
        assert_eq!(
            pvc_node.find_value("claimName"),
            Some("data-volume".to_string())
        );
    }

    #[test]
    fn test_heal_storage_class_binding_mode() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("StorageClass".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "volumeBindingMode".into(),
                        value: Some("Immediate".into()),
                        children: vec![],
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
        let changes = heal_storage_class_binding_modes(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert_eq!(
            manifest.root.find_value("volumeBindingMode"),
            Some("WaitForFirstConsumer".to_string())
        );
    }
}
