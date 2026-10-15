//! Job & CronJob RestartPolicy Contract Healer (Rule JOB-001 / Trap 56).
//!
//! Why: In Kubernetes, `PodSpec.restartPolicy` accepts `Always`, `OnFailure`, or `Never`.
//! However, the Kubernetes Batch API contract (`batch/v1` Job and CronJob) explicitly
//! requires that Pods managed by a Job MUST run to completion. Therefore:
//!
//! 1. `spec.template.spec.restartPolicy: Always` is strictly forbidden by the Job controller:
//!    `spec.template.spec.restartPolicy: Unsupported value: "Always": supported values: "OnFailure", "Never"`.
//! 2. Authors who copy Pod specs from Deployments or StatefulSets into Jobs frequently leave
//!    `restartPolicy: Always` (the Deployment default), causing instantaneous admission rejection.
//! 3. Yamlr normalizes `Always` under `Job.spec.template.spec` or `CronJob.spec.jobTemplate.spec.template.spec`
//!    to canonical `restartPolicy: OnFailure`, preserving batch retry behavior deterministically.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_JOB_001: &str = "JOB-001";
pub const RULE_JOB_002: &str = "JOB-002";
pub const RULE_JOB_003: &str = "JOB-003";

/// Reconciles `restartPolicy` on Job and CronJob workload pod templates.
pub fn heal_job_restart_policy(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Job" && kind != "CronJob" {
        return changes;
    }

    let workload_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-job".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if kind == "Job" {
            // Trap 63 / Rule JOB-002: spec.ttlSecondsAfterFinished integer unquoting & clamping >= 0
            if let Some(ttl_node) = spec.find_node_mut("ttlSecondsAfterFinished") {
                if let Some(val) = &ttl_node.value {
                    let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                    if let Ok(mut num) = clean.parse::<i64>() {
                        if num < 0 {
                            num = 0;
                        }
                        let canonical = num.to_string();
                        if *val != canonical {
                            let old_val = val.clone();
                            ttl_node.value = Some(canonical.clone());
                            for s in &mut ttl_node.shards {
                                s.value = Some(canonical.clone());
                            }
                            let msg = format!(
                                "Remediation [{}]: Unquoted/clamped Job '{}' ttlSecondsAfterFinished '{}' -> '{}'.",
                                RULE_JOB_002, workload_name, old_val, canonical
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }

            // Trap 64 / Rule JOB-003: spec.completionMode casing normalization (Indexed / NonIndexed)
            if let Some(cm_node) = spec.find_node_mut("completionMode") {
                if let Some(val) = &cm_node.value {
                    let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                    let canonical = if clean.eq_ignore_ascii_case("indexed") {
                        Some("Indexed")
                    } else if clean.eq_ignore_ascii_case("nonindexed") || clean.eq_ignore_ascii_case("non-indexed") {
                        Some("NonIndexed")
                    } else {
                        None
                    };

                    if let Some(canon_str) = canonical {
                        if val != canon_str {
                            let old_val = val.clone();
                            cm_node.value = Some(canon_str.to_string());
                            for s in &mut cm_node.shards {
                                s.value = Some(canon_str.to_string());
                            }
                            let msg = format!(
                                "Remediation [{}]: Normalized Job '{}' completionMode '{}' -> '{}'.",
                                RULE_JOB_003, workload_name, old_val, canon_str
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }

            if let Some(template) = spec.find_node_mut("template") {
                if let Some(pod_spec) = template.find_node_mut("spec") {
                    heal_pod_spec_restart_policy(pod_spec, &kind, &workload_name, telemetry, &mut changes);
                }
            }
        } else if kind == "CronJob" {
            if let Some(job_template) = spec.find_node_mut("jobTemplate") {
                if let Some(job_spec) = job_template.find_node_mut("spec") {
                    // Trap 63 on CronJob spec
                    if let Some(ttl_node) = job_spec.find_node_mut("ttlSecondsAfterFinished") {
                        if let Some(val) = &ttl_node.value {
                            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                            if let Ok(mut num) = clean.parse::<i64>() {
                                if num < 0 {
                                    num = 0;
                                }
                                let canonical = num.to_string();
                                if *val != canonical {
                                    let old_val = val.clone();
                                    ttl_node.value = Some(canonical.clone());
                                    for s in &mut ttl_node.shards {
                                        s.value = Some(canonical.clone());
                                    }
                                    let msg = format!(
                                        "Remediation [{}]: Unquoted/clamped CronJob '{}' ttlSecondsAfterFinished '{}' -> '{}'.",
                                        RULE_JOB_002, workload_name, old_val, canonical
                                    );
                                    native_record_healing_impact(telemetry, &msg);
                                    changes.push(msg);
                                }
                            }
                        }
                    }

                    if let Some(template) = job_spec.find_node_mut("template") {
                        if let Some(pod_spec) = template.find_node_mut("spec") {
                            heal_pod_spec_restart_policy(pod_spec, &kind, &workload_name, telemetry, &mut changes);
                        }
                    }
                }
            }
        }
    }

    changes
}

fn heal_pod_spec_restart_policy(
    pod_spec: &mut SemanticNode,
    kind: &str,
    workload_name: &str,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if let Some(rp_node) = pod_spec.find_node_mut("restartPolicy") {
        let current_val = rp_node.value.clone().unwrap_or_default();
        let clean = current_val.trim().trim_matches(|c| c == '\'' || c == '"');

        if clean.eq_ignore_ascii_case("always") {
            let canonical = "OnFailure".to_string();
            rp_node.value = Some(canonical.clone());
            for s in &mut rp_node.shards {
                s.value = Some(canonical.clone());
            }
            let msg = format!(
                "Remediation [{}]: Normalized forbidden 'restartPolicy: {}' -> 'OnFailure' in {} '{}' pod template.",
                RULE_JOB_001, current_val, kind, workload_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    } else {
        // If restartPolicy is missing in Job template, inject OnFailure to prevent admission failure
        let p_indent = pod_spec.indent;
        pod_spec.children.insert(
            0,
            SemanticNode {
                key: "restartPolicy".to_string(),
                value: Some("OnFailure".to_string()),
                indent: p_indent + 2,
                is_empty_flow: false,
                children: Vec::new(),
                shards: Vec::new(),
            },
        );
        let msg = format!(
            "Remediation [{}]: Injected required 'restartPolicy: OnFailure' in {} '{}' pod template.",
            RULE_JOB_001, kind, workload_name
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_job_restart_policy_always_to_on_failure() {
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
                        key: "kind".to_string(),
                        value: Some("Job".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "metadata".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "name".to_string(),
                            value: Some("data-migrate".to_string()),
                            indent: 2,
                            is_empty_flow: false,
                            children: Vec::new(),
                            shards: Vec::new(),
                        }],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "template".to_string(),
                            value: None,
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "spec".to_string(),
                                value: None,
                                indent: 4,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "restartPolicy".to_string(),
                                    value: Some("Always".to_string()),
                                    indent: 6,
                                    is_empty_flow: false,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                }],
                            }],
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_job_restart_policy(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Normalized forbidden 'restartPolicy: Always' -> 'OnFailure'"));

        let template_spec = manifest
            .root
            .find_node("spec")
            .unwrap()
            .find_node("template")
            .unwrap()
            .find_node("spec")
            .unwrap();
        assert_eq!(template_spec.find_value("restartPolicy"), Some("OnFailure".to_string()));
    }

    #[test]
    fn test_job_ttl_and_completion_mode() {
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
                        key: "kind".to_string(),
                        value: Some("Job".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "metadata".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "name".to_string(),
                            value: Some("batch-processor".to_string()),
                            indent: 2,
                            is_empty_flow: false,
                            children: Vec::new(),
                            shards: Vec::new(),
                        }],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "ttlSecondsAfterFinished".to_string(),
                                value: Some("\"300\"".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                            SemanticNode {
                                key: "completionMode".to_string(),
                                value: Some("\"indexed\"".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                            SemanticNode {
                                key: "template".to_string(),
                                value: None,
                                indent: 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "spec".to_string(),
                                    value: None,
                                    indent: 4,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "restartPolicy".to_string(),
                                        value: Some("Never".to_string()),
                                        indent: 6,
                                        is_empty_flow: false,
                                        children: Vec::new(),
                                        shards: Vec::new(),
                                    }],
                                }],
                            },
                        ],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_job_restart_policy(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 2);
        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(spec.find_value("ttlSecondsAfterFinished"), Some("300".to_string()));
        assert_eq!(spec.find_value("completionMode"), Some("Indexed".to_string()));
    }
}
