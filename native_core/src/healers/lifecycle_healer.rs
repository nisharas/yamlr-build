//! Graceful Termination & PreStop Hook Synchronizer (Feature 20).
//!
//! Why: When a container executes a `preStop` hook (e.g. `sleep 20` for endpoint draining),
//! if `spec.terminationGracePeriodSeconds` is omitted (defaults to 30s) or shorter than
//! the preStop duration, kubelet sends SIGKILL mid-shutdown, causing HTTP 502/504 errors.
//! This healer synchronizes termination grace periods with preStop drain durations.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const LIFECYCLE_RULE_ID: &str = "OPS-004";

/// Helper: Extracts sleep duration from a preStop command list if present.
pub fn extract_prestop_sleep_seconds(container: &SemanticNode) -> Option<u32> {
    if let Some(lifecycle) = container.find_node("lifecycle") {
        if let Some(pre_stop) = lifecycle.find_node("preStop") {
            if let Some(exec) = pre_stop.find_node("exec") {
                if let Some(cmd) = exec.find_node("command") {
                    // 1. Flow-style command: command: ["/bin/sh", "-c", "sleep 45"]
                    if let Some(ref val_text) = cmd.value {
                        let parts: Vec<&str> = val_text
                            .split(|c: char| {
                                c == ' '
                                    || c == '"'
                                    || c == '\''
                                    || c == '['
                                    || c == ']'
                                    || c == ','
                            })
                            .filter(|p| !p.is_empty())
                            .collect();
                        for (idx, &part) in parts.iter().enumerate() {
                            if part == "sleep" {
                                if let Some(&next) = parts.get(idx + 1) {
                                    if let Ok(sec) = next.parse::<u32>() {
                                        if sec > 0 && sec <= 300 {
                                            return Some(sec);
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // 2. Block-style sequence children: - "/bin/sh" \n - "sleep 45"
                    for arg in &cmd.children {
                        if let Some(ref text) = arg.value {
                            let parts: Vec<&str> = text.split_whitespace().collect();
                            for (idx, &part) in parts.iter().enumerate() {
                                if part == "sleep" {
                                    if let Some(&next) = parts.get(idx + 1) {
                                        if let Ok(sec) = next.parse::<u32>() {
                                            if sec > 0 && sec <= 300 {
                                                return Some(sec);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    None
}

/// Primary entrypoint: Synchronizes terminationGracePeriodSeconds with container preStop hooks.
pub fn heal_lifecycle_grace_periods(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    for spec in manifest.root.find_pod_specs_mut() {
        let mut max_prestop_sleep = 0;
        let mut has_prestop = false;

        if let Some(containers) = spec.find_node("containers") {
            for c in &containers.children {
                if let Some(sleep_sec) = extract_prestop_sleep_seconds(c) {
                    has_prestop = true;
                    if sleep_sec > max_prestop_sleep {
                        max_prestop_sleep = sleep_sec;
                    }
                } else if c
                    .find_node("lifecycle")
                    .and_then(|l| l.find_node("preStop"))
                    .is_some()
                {
                    has_prestop = true;
                }
            }
        }

        if !has_prestop || max_prestop_sleep == 0 {
            // Safety guard: If no preStop hook exists, or if the hook does not specify a measurable sleep duration
            // (e.g. an instantaneous script or httpGet probe), do not blindly alter or inject grace periods.
            continue;
        }

        let current_grace = spec
            .find_value("terminationGracePeriodSeconds")
            .and_then(|v| v.parse::<u32>().ok());

        // Kubernetes default terminationGracePeriodSeconds is 30s.
        let effective_grace = current_grace.unwrap_or(30);

        // If the effective grace period is already greater than the sleep duration,
        // kubelet will not prematurely SIGKILL the container during drain - preserve author's intent!
        if effective_grace > max_prestop_sleep {
            continue;
        }

        let recommended_grace = max_prestop_sleep + 15;
            let spec_indent = spec.indent;
            if let Some(grace_node) = spec.find_node_mut("terminationGracePeriodSeconds") {
                let old_val = grace_node.value.clone().unwrap_or_default();
                grace_node.value = Some(recommended_grace.to_string());
                for s in &mut grace_node.shards {
                    s.value = Some(recommended_grace.to_string());
                }
                let msg = format!(
                    "Remediation [{}]: Adjusted 'terminationGracePeriodSeconds' {}s -> {}s to accommodate preStop drain hook.",
                    LIFECYCLE_RULE_ID, old_val, recommended_grace
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            } else {
                spec.children.push(SemanticNode {
                    key: "terminationGracePeriodSeconds".to_string(),
                    value: Some(recommended_grace.to_string()),
                    indent: spec_indent + 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                });
                let msg = format!(
                    "Remediation [{}]: Injected 'terminationGracePeriodSeconds: {}' to prevent premature SIGKILL during preStop hook execution.",
                    LIFECYCLE_RULE_ID, recommended_grace
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
    fn test_synchronize_termination_grace_period() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "spec".to_string(),
                    value: None,
                    indent: 0,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "containers".to_string(),
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
                                    value: Some("web".to_string()),
                                    indent: 6,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                },
                                SemanticNode {
                                    key: "lifecycle".to_string(),
                                    value: None,
                                    indent: 6,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "preStop".to_string(),
                                        value: None,
                                        indent: 8,
                                        is_empty_flow: false,
                                        shards: Vec::new(),
                                        children: vec![SemanticNode {
                                            key: "exec".to_string(),
                                            value: None,
                                            indent: 10,
                                            is_empty_flow: false,
                                            shards: Vec::new(),
                                            children: vec![SemanticNode {
                                                key: "command".to_string(),
                                                value: None,
                                                indent: 12,
                                                is_empty_flow: false,
                                                shards: Vec::new(),
                                                children: vec![
                                                    SemanticNode {
                                                        key: "-".to_string(),
                                                        value: Some("/bin/sh".to_string()),
                                                        indent: 14,
                                                        is_empty_flow: false,
                                                        children: vec![],
                                                        shards: vec![],
                                                    },
                                                    SemanticNode {
                                                        key: "-".to_string(),
                                                        value: Some("-c".to_string()),
                                                        indent: 14,
                                                        is_empty_flow: false,
                                                        children: vec![],
                                                        shards: vec![],
                                                    },
                                                    SemanticNode {
                                                        key: "-".to_string(),
                                                        value: Some("sleep 30".to_string()),
                                                        indent: 14,
                                                        is_empty_flow: false,
                                                        children: vec![],
                                                        shards: vec![],
                                                    },
                                                ],
                                            }],
                                        }],
                                    }],
                                },
                            ],
                        }],
                    }],
                }],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_lifecycle_grace_periods(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);

        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(
            spec.find_value("terminationGracePeriodSeconds"),
            Some("45".to_string())
        );
    }
}
