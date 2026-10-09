//! DaemonSet Update Strategy Modernizer (Rule REL-012).
//!
//! Why: In Kubernetes, DaemonSets configured with `updateStrategy.type: OnDelete` (or missing
//! updateStrategy defaulting to legacy behavior) do not automatically replace pods when the manifest changes.
//! Upgrading to `RollingUpdate` prevents stale versions and cluster inconsistencies.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const DAEMONSET_UPDATE_RULE_ID: &str = "REL-012";

/// Heals DaemonSet update strategy to ensure RollingUpdate is used.
pub fn heal_daemonset_update_strategy(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "DaemonSet" {
        return changes;
    }

    let ds_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-daemonset".to_string());

    let opt_in = manifest
        .root
        .find_annotation("yamlr.dev/upgrade-on-delete")
        .or_else(|| manifest.root.find_annotation("yamlr.io/upgrade-on-delete"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(strategy) = spec.find_node_mut("updateStrategy") {
            let current_type = strategy.find_value("type").unwrap_or_default();
            let clean_type = current_type.trim().trim_matches('"').trim_matches('\'');
            if clean_type == "OnDelete" && opt_in {
                if let Some(type_node) = strategy.find_node_mut("type") {
                    type_node.value = Some("RollingUpdate".to_string());
                    for s in &mut type_node.shards {
                        s.value = Some("RollingUpdate".to_string());
                    }
                    let msg = format!(
                        "Remediation [{}]: Upgraded DaemonSet '{}' updateStrategy from 'OnDelete' to 'RollingUpdate'.",
                        DAEMONSET_UPDATE_RULE_ID, ds_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        } else {
            // Missing updateStrategy completely -> inject RollingUpdate
            let indent = spec.indent + 2;
            spec.children.push(SemanticNode {
                key: "updateStrategy".to_string(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "type".to_string(),
                        value: Some("RollingUpdate".to_string()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent: indent + 2,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "rollingUpdate".to_string(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "maxUnavailable".to_string(),
                            value: Some("1".to_string()),
                            children: Vec::new(),
                            shards: Vec::new(),
                            indent: indent + 4,
                            is_empty_flow: false,
                        }],
                        shards: Vec::new(),
                        indent: indent + 2,
                        is_empty_flow: false,
                    },
                ],
                shards: Vec::new(),
                indent,
                is_empty_flow: false,
            });
            let msg = format!(
                "Remediation [{}]: Injected standard 'RollingUpdate' strategy into DaemonSet '{}'.",
                DAEMONSET_UPDATE_RULE_ID, ds_name
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
    fn test_inject_daemonset_rolling_update() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("DaemonSet".into()),
                        children: vec![],
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
        let changes = heal_daemonset_update_strategy(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        let strat = spec.find_node("updateStrategy").unwrap();
        assert_eq!(strat.find_value("type"), Some("RollingUpdate".to_string()));
    }
}
