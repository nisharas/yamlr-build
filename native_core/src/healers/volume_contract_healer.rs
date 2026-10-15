//! Volume & Storage Contract Healer (Rules SEC-023, VOL-001 / Traps 61, 65).
//!
//! Why:
//! 1. Rule SEC-023 (Trap 61): In `spec.volumes[*].hostPath`, omitting `type` defaults to `""` (Unset),
//!    which bypasses path pre-flight validation in kubelet and allows directory escapes.
//!    Enforcing an explicit `type: DirectoryOrCreate` or `FileOrCreate` satisfies security standards.
//! 2. Rule VOL-001 (Trap 65): In `spec.volumes[*].emptyDir.medium`, Kubernetes strictly requires
//!    `""` (default storage) or `"Memory"` (tmpfs). Developers often write `"memory"` (lowercase) or
//!    `"ram"`, causing kubelet to reject pod creation: `invalid emptyDir medium`.
//!    This healer normalizes case-insensitive `memory` and `ram` to canonical `Memory`.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_SEC_023: &str = "SEC-023";
pub const RULE_VOL_001: &str = "VOL-001";

/// Primary entrypoint: Enforces storage volume type contracts.
pub fn heal_volume_contracts(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    heal_volume_contracts_recursive(&mut manifest.root, telemetry, &mut changes);
    changes
}

fn heal_volume_contracts_recursive(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "volumes" {
        for vol_item in &mut node.children {
            let vol_name = vol_item
                .find_value("name")
                .unwrap_or_else(|| "unnamed-volume".to_string());

            // Trap 65 / Rule VOL-001: emptyDir.medium casing
            if let Some(empty_dir) = vol_item.find_node_mut("emptyDir") {
                if let Some(med_node) = empty_dir.find_node_mut("medium") {
                    if let Some(val) = &med_node.value {
                        let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                        if clean.eq_ignore_ascii_case("memory") || clean.eq_ignore_ascii_case("ram") {
                            if *val != "Memory" {
                                let old_val = val.clone();
                                med_node.value = Some("Memory".to_string());
                                for s in &mut med_node.shards {
                                    s.value = Some("Memory".to_string());
                                }
                                let msg = format!(
                                    "Remediation [{}]: Normalized emptyDir medium '{}' -> 'Memory' on volume '{}'.",
                                    RULE_VOL_001, old_val, vol_name
                                );
                                native_record_healing_impact(telemetry, &msg);
                                changes.push(msg);
                            }
                        }
                    }
                }
            }

            // Trap 61 / Rule SEC-023: hostPath missing explicit type
            if let Some(host_path) = vol_item.find_node_mut("hostPath") {
                if host_path.find_node("type").is_none() {
                    let path_val = host_path.find_value("path").unwrap_or_default();
                    let clean_path = path_val.trim().trim_matches(|c| c == '\'' || c == '"');
                    let chosen_type = if clean_path.ends_with(".sock")
                        || clean_path.ends_with(".pid")
                        || clean_path.ends_with(".conf")
                        || clean_path.contains('.')
                    {
                        "FileOrCreate"
                    } else {
                        "DirectoryOrCreate"
                    };

                    let hp_indent = host_path.indent;
                    host_path.children.push(SemanticNode {
                        key: "type".to_string(),
                        value: Some(chosen_type.to_string()),
                        indent: hp_indent + 2,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    });

                    let msg = format!(
                        "Remediation [{}]: Injected explicit hostPath 'type: {}' on volume '{}' to satisfy path validation contracts.",
                        RULE_SEC_023, chosen_type, vol_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    for child in &mut node.children {
        heal_volume_contracts_recursive(child, telemetry, changes);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heal_emptydir_medium_casing() {
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
                        key: "volumes".to_string(),
                        value: None,
                        indent: 2,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "-".to_string(),
                            value: None,
                            indent: 4,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![
                                SemanticNode {
                                    key: "name".to_string(),
                                    value: Some("cache-vol".to_string()),
                                    indent: 6,
                                    is_empty_flow: false,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                },
                                SemanticNode {
                                    key: "emptyDir".to_string(),
                                    value: None,
                                    indent: 6,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "medium".to_string(),
                                        value: Some("\"memory\"".to_string()),
                                        indent: 8,
                                        is_empty_flow: false,
                                        children: Vec::new(),
                                        shards: Vec::new(),
                                    }],
                                },
                            ],
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_volume_contracts(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Normalized emptyDir medium"));

        let vols = manifest.root.find_node("volumes").unwrap();
        let ed = vols.children[0].find_node("emptyDir").unwrap();
        assert_eq!(ed.find_value("medium"), Some("Memory".to_string()));
    }
}
