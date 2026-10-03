//! PodDisruptionBudget Deadlock Preventer (Feature 16).
//!
//! Why: A PodDisruptionBudget with `minAvailable: 100%` or `maxUnavailable: 0`
//! (or `minAvailable >= replicas` on a low-replica workload) completely halts
//! `kubectl drain`, node rolling upgrades, and cluster autoscaling.
//! This healer normalizes impossible PDB constraints into safe disruption policies.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const PDB_RULE_ID: &str = "REL-005";

/// Primary entrypoint: Heals deadlock-prone PodDisruptionBudget manifests.
pub fn heal_pdb_deadlocks(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "PodDisruptionBudget" {
        return changes;
    }

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        let mut min_avail_val = None;
        let mut max_unavail_val = None;

        if let Some(min_node) = spec.find_node("minAvailable") {
            min_avail_val = min_node.value.clone();
        }
        if let Some(max_node) = spec.find_node("maxUnavailable") {
            max_unavail_val = max_node.value.clone();
        }

        // 1. Check maxUnavailable: 0 or "0%" -> Heals to 1
        if let Some(ref val) = max_unavail_val {
            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
            if clean == "0" || clean == "0%" {
                if let Some(max_node) = spec.find_node_mut("maxUnavailable") {
                    max_node.value = Some("1".to_string());
                    for s in &mut max_node.shards {
                        s.value = Some("1".to_string());
                    }
                    let msg = format!(
                        "Remediation [{}]: Healed deadlock 'maxUnavailable: {}' -> '1' on PodDisruptionBudget.",
                        PDB_RULE_ID, clean
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }

        // 2. Check minAvailable: 100% -> Heals to 50% or maxUnavailable: 1
        if let Some(ref val) = min_avail_val {
            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
            if clean == "100%" {
                if let Some(min_node) = spec.find_node_mut("minAvailable") {
                    min_node.value = Some("50%".to_string());
                    for s in &mut min_node.shards {
                        s.value = Some("50%".to_string());
                    }
                    let msg = format!(
                        "Remediation [{}]: Relaxed deadlock 'minAvailable: 100%' -> '50%' on PodDisruptionBudget to permit node evictions.",
                        PDB_RULE_ID
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    changes
}

/// Cross-resource aware PDB deadlock healer: verifies against target workload replica count.
pub fn heal_pdb_with_workload_replicas(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = heal_pdb_deadlocks(manifest, telemetry);

    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "PodDisruptionBudget" {
        return changes;
    }

    // Inspect selector matchLabels to find matching workload
    let mut match_labels = std::collections::HashMap::new();
    if let Some(spec) = manifest.root.find_node("spec") {
        if let Some(sel) = spec.find_node("selector") {
            if let Some(ml) = sel.find_node("matchLabels") {
                for child in &ml.children {
                    if let Some(ref v) = child.value {
                        match_labels.insert(child.key.clone(), v.clone());
                    }
                }
            }
        }
    }

    if match_labels.is_empty() {
        return changes;
    }

    // Find target workload in same namespace
    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let target_workload = identities.iter().find(|id| {
        id.namespace == ns
            && !id.labels.is_empty()
            && match_labels
                .iter()
                .all(|(k, v)| id.labels.get(k) == Some(v))
    });

    if let Some(workload) = target_workload {
        let workload_replicas = workload.replicas.unwrap_or(1);

        if let Some(spec) = manifest.root.find_node_mut("spec") {
            if let Some(min_node) = spec.find_node_mut("minAvailable") {
                if let Some(ref v) = min_node.value {
                    let clean = v.trim().trim_matches(|c| c == '\'' || c == '"');
                    if let Ok(min_avail_num) = clean.parse::<i32>() {
                        // Deadlock condition: minAvailable >= workload_replicas
                        if min_avail_num >= workload_replicas {
                            let safe_val = if workload_replicas <= 1 {
                                ("maxUnavailable".to_string(), "1".to_string())
                            } else {
                                (
                                    "minAvailable".to_string(),
                                    (workload_replicas - 1).to_string(),
                                )
                            };

                            let old_key = min_node.key.clone();
                            let old_val = clean.to_string();

                            min_node.key = safe_val.0.clone();
                            min_node.value = Some(safe_val.1.clone());
                            for s in &mut min_node.shards {
                                s.key = safe_val.0.clone();
                                s.value = Some(safe_val.1.clone());
                            }

                            let msg = format!(
                                "Remediation [{}]: Resolved PDB deadlock '{}: {}' >= {} replicas on workload '{}' -> '{}: {}'.",
                                PDB_RULE_ID, old_key, old_val, workload_replicas, workload.name, safe_val.0, safe_val.1
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
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
    fn test_heal_max_unavailable_zero() {
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
                        value: Some("PodDisruptionBudget".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "maxUnavailable".to_string(),
                            value: Some("0".to_string()),
                            indent: 2,
                            is_empty_flow: false,
                            children: vec![],
                            shards: vec![],
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_pdb_deadlocks(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        let max_unavail = spec.find_node("maxUnavailable").unwrap();
        assert_eq!(max_unavail.value, Some("1".to_string()));
    }

    #[test]
    fn test_heal_min_available_100_percent() {
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
                        value: Some("PodDisruptionBudget".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "minAvailable".to_string(),
                            value: Some("100%".to_string()),
                            indent: 2,
                            is_empty_flow: false,
                            children: vec![],
                            shards: vec![],
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_pdb_deadlocks(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        let min_avail = spec.find_node("minAvailable").unwrap();
        assert_eq!(min_avail.value, Some("50%".to_string()));
    }

    #[test]
    fn test_heal_min_available_greater_than_or_equal_to_replicas() {
        let mut telemetry = NativeTelemetry::default();
        let yaml = r#"
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
  namespace: prod
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: api-server
"#;
        let mut manifest =
            crate::structurer::native_structurize(crate::sharder::native_shard(yaml));
        let mut labels = std::collections::HashMap::new();
        labels.insert("app".to_string(), "api-server".to_string());

        let target_workload = NativeIdentity {
            kind: "Deployment".to_string(),
            name: "api-server".to_string(),
            namespace: "prod".to_string(),
            labels,
            replicas: Some(3),
            ..Default::default()
        };

        let changes =
            heal_pdb_with_workload_replicas(&mut manifest, &[target_workload], &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Resolved PDB deadlock 'minAvailable: 3' >= 3 replicas"));

        let spec = manifest.root.find_node("spec").unwrap();
        let min_avail = spec.find_node("minAvailable").unwrap();
        assert_eq!(min_avail.value, Some("2".to_string()));
    }
}
