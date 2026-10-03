//! Workload ServiceAccount Reference Healer (Rule SEC-011).
//!
//! Why: Using the deprecated `serviceAccount` field instead of `serviceAccountName`, or typos
//! in `serviceAccountName`, causes Kubernetes to reject pod creation with `serviceaccount not found`.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const SA_REF_RULE_ID: &str = "SEC-011";
pub const SA_SIMILARITY_THRESHOLD: f64 = 0.75;

/// Recursively aligns serviceAccountName and modernizes deprecated serviceAccount fields.
fn align_workload_sa_recursive(
    node: &mut SemanticNode,
    ns: &str,
    sas: &[&NativeIdentity],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    // 1. Modernize deprecated serviceAccount field
    if let Some(pos) = node.children.iter().position(|c| c.key == "serviceAccount") {
        let old_node = &node.children[pos];
        let sa_val = old_node.value.clone().unwrap_or_default();
        node.children[pos].key = "serviceAccountName".to_string();
        for s in &mut node.children[pos].shards {
            s.key = "serviceAccountName".to_string();
        }
        let msg = format!(
            "Remediation [{}]: Modernized deprecated 'serviceAccount: {}' to 'serviceAccountName'.",
            SA_REF_RULE_ID, sa_val
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }

    // 2. Fuzzy align serviceAccountName typos
    if let Some(sa_node) = node.find_node_mut("serviceAccountName") {
        let current = sa_node.value.clone().unwrap_or_default();
        let clean = current.trim().trim_matches('"').trim_matches('\'');

        if !clean.is_empty()
            && clean != "default"
            && !sas.iter().any(|s| s.name == clean)
            && !sas.is_empty()
        {
            let mut best_target = None;
            let mut best_ratio = 0.0;
            for s in sas {
                let ratio = crate::healers::selector_healer::similarity_ratio(clean, &s.name);
                if ratio >= SA_SIMILARITY_THRESHOLD && ratio > best_ratio {
                    best_ratio = ratio;
                    best_target = Some(s.name.clone());
                }
            }

            if let Some(target) = best_target {
                sa_node.value = Some(target.clone());
                for s in &mut sa_node.shards {
                    s.value = Some(target.clone());
                }
                let msg = format!(
                    "Remediation [{}]: Aligned serviceAccountName '{}' -> '{}' in namespace '{}' (similarity: {:.2}).",
                    SA_REF_RULE_ID, clean, target, ns, best_ratio
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    for child in &mut node.children {
        align_workload_sa_recursive(child, ns, sas, telemetry, changes);
    }
}

/// Primary Entrypoint: Aligns all broken ServiceAccount references in workload specs.
pub fn heal_service_account_references(
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

    let sas: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| {
            id.kind == "ServiceAccount"
                && (id.namespace == ns || id.namespace.is_empty() || id.namespace == "default")
        })
        .collect();

    align_workload_sa_recursive(&mut manifest.root, &ns, &sas, telemetry, &mut changes);
    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_modernize_deprecated_service_account() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![SemanticNode {
                    key: "serviceAccount".into(),
                    value: Some("my-sa".into()),
                    children: vec![],
                    shards: vec![],
                    indent: 0,
                    is_empty_flow: false,
                }],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            indent_step: 2,
            integrity_violations: vec![],
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_service_account_references(&mut manifest, &[], &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(manifest.root.find_node("serviceAccountName").is_some());
        assert!(manifest.root.find_node("serviceAccount").is_none());
    }
}
