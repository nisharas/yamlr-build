//! Storage SubPath, Scientific Float, Map-to-Array, and CronJob Healers (Rules STO-005, STO-006, TYP-003, SYN-009, OPS-004, OPS-005).
//!
//! Why:
//! 1. STO-005: Mounting ConfigMaps directly over `/etc/nginx` without subPath overwrites and masks default image files.
//! 2. STO-006: AWS EBS or GCP PersistentDisks do not support ReadWriteMany (RWX), causing volume attachment deadlocks.
//! 3. TYP-003: Helm scientific float notation (`0.001` or `1e-3`) is rejected by Kubernetes quantity schema.
//! 4. SYN-009: Missing hyphens on `ports:` or `env:` parse as a map instead of an array.
//! 5. OPS-004: Missing `spec.timeZone` on CronJobs causes DST 1-hour scheduling shifts.
//! 6. OPS-005: Default `concurrencyPolicy: Allow` causes heavy batch jobs to overlap and crash nodes.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_STO_006: &str = "STO-006";
pub const RULE_STO_007: &str = "STO-007";
pub const RULE_STO_008: &str = "STO-008";
pub const RULE_TYP_003: &str = "TYP-003";
pub const RULE_SYN_009: &str = "SYN-009";
pub const RULE_OPS_004: &str = "OPS-004";
pub const RULE_OPS_005: &str = "OPS-005";

/// Heals CronJob timezone specification and concurrency policies (Rules OPS-004, OPS-005).
pub fn heal_cronjob_operational_invariants(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "CronJob" {
        return changes;
    }

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        let s_indent = spec.indent;

        // OPS-005: ConcurrencyPolicy Forbid by default on long batch jobs
        if spec.find_node("concurrencyPolicy").is_none() {
            spec.children.push(SemanticNode {
                key: "concurrencyPolicy".to_string(),
                value: Some("Forbid".to_string()),
                indent: s_indent + 2,
                is_empty_flow: false,
                children: Vec::new(),
                shards: Vec::new(),
            });
            let msg = format!(
                "Remediation [{}]: Enforced 'concurrencyPolicy: Forbid' on CronJob to prevent cascading concurrent execution storms.",
                RULE_OPS_005
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }

        // OPS-004: Stamp explicit timeZone if missing (K8s 1.27+)
        if spec.find_node("timeZone").is_none() {
            spec.children.push(SemanticNode {
                key: "timeZone".to_string(),
                value: Some("\"Etc/UTC\"".to_string()),
                indent: s_indent + 2,
                is_empty_flow: false,
                children: Vec::new(),
                shards: Vec::new(),
            });
            let msg = format!(
                "Remediation [{}]: Stamped explicit 'timeZone: \"Etc/UTC\"' on CronJob to prevent DST scheduling drift.",
                RULE_OPS_004
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

/// Normalizes singleton maps under strict array keys into valid YAML sequence lists (Rule SYN-009).
pub fn heal_singleton_maps_to_arrays(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let target_keys = ["ports", "env", "volumeMounts"];
    for child in &mut node.children {
        if target_keys.contains(&child.key.as_str()) {
            // Check if child has children that are not list items and whose shards are not list items
            let is_already_array = child.children.iter().any(|c| {
                c.key == "-" || c.shards.first().map_or(false, |s| s.is_list_item)
            });

            if !child.children.is_empty() && !is_already_array {
                let old_children = std::mem::take(&mut child.children);
                let list_item = SemanticNode {
                    key: "-".to_string(),
                    value: None,
                    indent: child.indent + 2,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: old_children,
                };
                child.children.push(list_item);
                let msg = format!(
                    "Remediation [{}]: Converted singleton map under '{}' to a valid array of maps (- key: val).",
                    RULE_SYN_009, child.key
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
            if child.key == "env" {
                for item in &mut child.children {
                    for prop in &mut item.children {
                        if prop.key == "value" {
                            let should_quote = prop.value.as_deref().and_then(|val| {
                                let trimmed = val.trim();
                                if trimmed == "true" || trimmed == "false" {
                                    Some((trimmed.to_string(), format!("\"{}\"", trimmed)))
                                } else {
                                    None
                                }
                            });
                            if let Some((trimmed, quoted)) = should_quote {
                                prop.value = Some(quoted.clone());
                                for s in &mut prop.shards {
                                    s.value = Some(quoted.clone());
                                }
                                let msg = format!(
                                    "Remediation [TYP-005]: Quoted boolean env value '{}' to string '{}' to comply with Kubernetes EnvVar schema.",
                                    trimmed, quoted
                                );
                                native_record_healing_impact(telemetry, &msg);
                                changes.push(msg);
                            }
                        }
                    }
                }
            }
        }
        heal_singleton_maps_to_arrays(child, telemetry, changes);
    }
}

/// Converts scientific float notation or fractional decimals into standard Kubernetes integer millicores (Rule TYP-003).
pub fn heal_scientific_float_quantities(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "cpu" {
        if let Some(val) = &node.value {
            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
            // If it parses as a float with a decimal or exponent (e.g. "0.001", "1e-3")
            if (clean.contains('.') || clean.contains('e') || clean.contains('E')) && !clean.ends_with('m') {
                if let Ok(flt) = clean.parse::<f64>() {
                    let millis = (flt * 1000.0).round() as i64;
                    if millis > 0 {
                        let formatted = format!("\"{}m\"", millis);
                        let msg = format!(
                            "Remediation [{}]: Converted float CPU quantity '{}' to standard millicores '{}'.",
                            RULE_TYP_003, val, formatted
                        );
                        node.value = Some(formatted.clone());
                        for s in &mut node.shards {
                            s.value = Some(formatted.clone());
                        }
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    }

    for child in &mut node.children {
        heal_scientific_float_quantities(child, telemetry, changes);
    }
}

/// Rule STO-007 (Trap 35): Sanitizes illegal leading slashes in `volumeMounts[].subPath`.
/// Kubernetes subPath must be a relative path. If subPath starts with '/', kubelet fails pod startup.
/// Deterministic fix: Strip leading '/' from subPath while preserving the rest of the path.
pub fn heal_subpath_leading_slashes(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "subPath" || node.key == "subPathExpr" {
        let mutation = if let Some(val) = &node.value {
            let trimmed = val.trim();
            let has_quotes = trimmed.starts_with('"') || trimmed.starts_with('\'');
            let unquoted = trimmed.trim_matches(|c| c == '\'' || c == '"');

            if unquoted.starts_with('/') {
                let stripped_subpath = unquoted.trim_start_matches('/');
                if !stripped_subpath.is_empty() {
                    let new_val = if has_quotes {
                        format!("\"{}\"", stripped_subpath)
                    } else {
                        stripped_subpath.to_string()
                    };
                    Some((val.clone(), new_val))
                } else {
                    None
                }
            } else {
                None
            }
        } else {
            None
        };

        if let Some((old_val, new_val)) = mutation {
            node.value = Some(new_val.clone());
            for s in &mut node.shards {
                s.value = Some(new_val.clone());
            }

            let msg = format!(
                "Remediation [STO-007]: Stripped illegal leading slash from volumeMount {}: '{}' -> '{}'.",
                node.key, old_val, new_val
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    for child in &mut node.children {
        heal_subpath_leading_slashes(child, telemetry, changes);
    }
}

/// Rule STO-008 (Trap 39): Sanitizes POSIX octal file permission modes in `defaultMode` and `items[].mode`.
///
/// Why: In Kubernetes `volumes[*].configMap` or `volumes[*].secret`, developers write file permissions
/// using POSIX octal notation (e.g. `0755`, `"0755"`, `"644"`, `"0644"`). In YAML 1.2, unquoted `0755`
/// parses as decimal `755` (which is `01363` octal, corrupting execution bits). Furthermore, OpenAPI v3
/// strictly expects an integer scalar, rejecting quoted strings (`"0755"` -> `expected integer`).
///
/// This healer parses any valid POSIX octal permission notation and mathematically converts it
/// to its exact base-10 decimal integer (e.g. octal 644 -> decimal 420; octal 755 -> decimal 493).
pub fn heal_file_permission_modes(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "defaultMode" || node.key == "mode" {
        let mutation = if let Some(val) = &node.value {
            let trimmed = val.trim();
            let is_quoted = trimmed.starts_with('"') || trimmed.starts_with('\'');
            let clean = trimmed.trim_matches(|c| c == '\'' || c == '"');

            // Must be composed entirely of octal digits 0..=7 and between 3 to 4 digits
            let is_valid_octal = !clean.is_empty()
                && clean.len() <= 4
                && clean.chars().all(|c| ('0'..='7').contains(&c));

            if is_valid_octal {
                let has_leading_zero = clean.starts_with('0') && clean.len() >= 3;

                // Quoted ("0755", "644", "0644") OR unquoted with leading zero (0755, 0644)
                if is_quoted || has_leading_zero {
                    if let Ok(decimal_val) = i64::from_str_radix(clean, 8) {
                        if decimal_val <= 4095 {
                            let new_val = decimal_val.to_string();
                            if new_val != *val {
                                Some((val.clone(), new_val))
                            } else {
                                None
                            }
                        } else {
                            None
                        }
                    } else {
                        None
                    }
                } else {
                    None
                }
            } else {
                None
            }
        } else {
            None
        };

        if let Some((old_val, new_val)) = mutation {
            node.value = Some(new_val.clone());
            for s in &mut node.shards {
                s.value = Some(new_val.clone());
            }

            let msg = format!(
                "Remediation [{}]: Converted POSIX octal file permission mode '{}' to standard integer decimal '{}'.",
                RULE_STO_008, old_val, new_val
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    for child in &mut node.children {
        heal_file_permission_modes(child, telemetry, changes);
    }
}

/// Primary Entrypoint: Dispatches storage, Helm float, map-to-array, and CronJob healers.
pub fn heal_operational_and_storage_invariants(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    let cj_changes = heal_cronjob_operational_invariants(manifest, telemetry);
    changes.extend(cj_changes);

    heal_singleton_maps_to_arrays(&mut manifest.root, telemetry, &mut changes);
    heal_scientific_float_quantities(&mut manifest.root, telemetry, &mut changes);
    heal_subpath_leading_slashes(&mut manifest.root, telemetry, &mut changes);
    heal_file_permission_modes(&mut manifest.root, telemetry, &mut changes);

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heal_subpath_leading_slashes() {
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
                        key: "volumeMounts".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "-".into(),
                                value: None,
                                children: vec![
                                    SemanticNode {
                                        key: "name".into(),
                                        value: Some("config-vol".into()),
                                        children: vec![],
                                        shards: vec![],
                                        indent: 6,
                                        is_empty_flow: false,
                                    },
                                    SemanticNode {
                                        key: "mountPath".into(),
                                        value: Some("/etc/nginx/nginx.conf".into()),
                                        children: vec![],
                                        shards: vec![],
                                        indent: 6,
                                        is_empty_flow: false,
                                    },
                                    SemanticNode {
                                        key: "subPath".into(),
                                        value: Some("\"/nginx.conf\"".into()),
                                        children: vec![],
                                        shards: vec![],
                                        indent: 6,
                                        is_empty_flow: false,
                                    },
                                ],
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
        let changes = heal_operational_and_storage_invariants(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let vm = manifest.root.find_node("volumeMounts").unwrap();
        let item = &vm.children[0];
        assert_eq!(item.find_value("subPath"), Some("\"nginx.conf\"".to_string()));
    }

    #[test]
    fn test_heal_file_permission_modes() {
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
                        key: "volumes".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "-".into(),
                                value: None,
                                children: vec![
                                    SemanticNode {
                                        key: "name".into(),
                                        value: Some("config-vol".into()),
                                        children: vec![],
                                        shards: vec![],
                                        indent: 6,
                                        is_empty_flow: false,
                                    },
                                    SemanticNode {
                                        key: "configMap".into(),
                                        value: None,
                                        children: vec![
                                            SemanticNode {
                                                key: "defaultMode".into(),
                                                value: Some("\"0755\"".into()),
                                                children: vec![],
                                                shards: vec![],
                                                indent: 8,
                                                is_empty_flow: false,
                                            },
                                        ],
                                        shards: vec![],
                                        indent: 6,
                                        is_empty_flow: false,
                                    },
                                ],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "-".into(),
                                value: None,
                                children: vec![
                                    SemanticNode {
                                        key: "name".into(),
                                        value: Some("secret-vol".into()),
                                        children: vec![],
                                        shards: vec![],
                                        indent: 6,
                                        is_empty_flow: false,
                                    },
                                    SemanticNode {
                                        key: "secret".into(),
                                        value: None,
                                        children: vec![
                                            SemanticNode {
                                                key: "defaultMode".into(),
                                                value: Some("\"644\"".into()),
                                                children: vec![],
                                                shards: vec![],
                                                indent: 8,
                                                is_empty_flow: false,
                                            },
                                        ],
                                        shards: vec![],
                                        indent: 6,
                                        is_empty_flow: false,
                                    },
                                ],
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
        let changes = heal_operational_and_storage_invariants(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 2);

        let vols = manifest.root.find_node("volumes").unwrap();
        let cm = vols.children[0].find_node("configMap").unwrap();
        assert_eq!(cm.find_value("defaultMode"), Some("493".to_string()));

        let sec = vols.children[1].find_node("secret").unwrap();
        assert_eq!(sec.find_value("defaultMode"), Some("420".to_string()));
    }
}
