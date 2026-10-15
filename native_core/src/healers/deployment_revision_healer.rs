//! Workload Revision History Limit Healer (Rule REL-013).
//!
//! Why: Deployments and StatefulSets with unbounded or excessively high `revisionHistoryLimit`
//! retain hundreds of inactive ReplicaSets in etcd, bloating memory and degrading Kubernetes apiserver
//! listing performance. Enforcing `revisionHistoryLimit: 10` keeps etcd lean while retaining rollback capability.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const REVISION_HISTORY_RULE_ID: &str = "REL-013";

/// Enforces reasonable revisionHistoryLimit (10) on Deployment and StatefulSet workloads.
pub fn heal_deployment_revision_limits(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Deployment" && kind != "StatefulSet" {
        return changes;
    }

    let workload_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-workload".to_string());

    let enforce_missing = manifest
        .root
        .find_annotation("yamlr.io/enforce-revision-limits")
        .or_else(|| manifest.root.find_annotation("yamlr.io/revision-history"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(rev_node) = spec.find_node_mut("revisionHistoryLimit") {
            let val = rev_node.value.clone().unwrap_or_default();
            if let Ok(num) = val
                .trim()
                .trim_matches('"')
                .trim_matches('\'')
                .parse::<i32>()
            {
                if num < 0 {
                    rev_node.value = Some("0".to_string());
                    for s in &mut rev_node.shards {
                        s.value = Some("0".to_string());
                    }
                    let msg = format!(
                        "Remediation [{}]: Corrected invalid negative revisionHistoryLimit: {} -> 0 on {} '{}'.",
                        REVISION_HISTORY_RULE_ID, num, kind, workload_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        } else if enforce_missing {
            let indent = spec.indent + 2;
            spec.children.push(SemanticNode {
                key: "revisionHistoryLimit".to_string(),
                value: Some("10".to_string()),
                children: Vec::new(),
                shards: Vec::new(),
                indent,
                is_empty_flow: false,
            });
            let msg = format!(
                "Remediation [{}]: Enforced 'revisionHistoryLimit: 10' on {} '{}'.",
                REVISION_HISTORY_RULE_ID, kind, workload_name
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
    fn test_inject_revision_history_limit() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Deployment".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "annotations".into(),
                            value: None,
                            children: vec![SemanticNode {
                                key: "yamlr.io/enforce-revision-limits".into(),
                                value: Some("\"true\"".into()),
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
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
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
        let changes = heal_deployment_revision_limits(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(
            spec.find_value("revisionHistoryLimit"),
            Some("10".to_string())
        );
    }
}
