//! PodDisruptionBudget maxUnavailable Deadlock & Mutual Exclusion Healer (Rule REL-005).
//!
//! Why: In Kubernetes, configuring `maxUnavailable: 0` prevents any pod from being evicted,
//! causing `kubectl drain` and cluster upgrades to hang forever. Additionally, specifying both
//! `minAvailable` and `maxUnavailable` at the same time is rejected by Kubernetes schema validation.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const PDB_MAX_UNAVAIL_RULE_ID: &str = "REL-005";

/// Heals PDB maxUnavailable: 0 and mutual exclusion violations.
pub fn heal_pdb_max_unavailable(
    manifest: &mut SemanticManifest,
    _identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "PodDisruptionBudget" {
        return changes;
    }

    let pdb_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-pdb".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        let has_min = spec.find_node("minAvailable").is_some();
        let has_max = spec.find_node("maxUnavailable").is_some();

        // 1. Mutual Exclusion: If both minAvailable and maxUnavailable exist, remove maxUnavailable
        if has_min && has_max {
            if let Some(pos) = spec.children.iter().position(|c| c.key == "maxUnavailable") {
                spec.children.remove(pos);
                let msg = format!(
                    "Remediation [{}]: Removed conflicting 'maxUnavailable' (both minAvailable and maxUnavailable defined) in PDB '{}'.",
                    PDB_MAX_UNAVAIL_RULE_ID, pdb_name
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        } else if let Some(max_node) = spec.find_node_mut("maxUnavailable") {
            // 2. Check for maxUnavailable: 0 or "0%"
            let current = max_node.value.clone().unwrap_or_default();
            let clean = current.trim().trim_matches('"').trim_matches('\'');
            if clean == "0" || clean == "0%" {
                max_node.value = Some("1".to_string());
                for s in &mut max_node.shards {
                    s.value = Some("1".to_string());
                }
                let msg = format!(
                    "Remediation [{}]: Healed deadlock 'maxUnavailable: {}' -> '1' in PDB '{}'.",
                    PDB_MAX_UNAVAIL_RULE_ID, clean, pdb_name
                );
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
    use crate::models::SemanticNode;

    #[test]
    fn test_remove_mutual_exclusion_conflict() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("PodDisruptionBudget".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "minAvailable".into(),
                                value: Some("1".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "maxUnavailable".into(),
                                value: Some("1".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            },
                        ],
                        shards: vec![],
                        indent: 2,
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
        let changes = heal_pdb_max_unavailable(&mut manifest, &[], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        assert!(spec.find_node("maxUnavailable").is_none());
        assert!(spec.find_node("minAvailable").is_some());
    }
}
