//! Session Affinity Contract & ClientIP Mismatch Healer (Rule NET-015 / Trap 55).
//!
//! Why: In Kubernetes `Service`, `spec.sessionAffinity` and `spec.sessionAffinityConfig`
//! have a strict mutually dependent schema contract:
//!
//! 1. `spec.sessionAffinityConfig` is only allowed when `spec.sessionAffinity` is `ClientIP`.
//!    If `sessionAffinityConfig` is defined while `sessionAffinity` is omitted or set to `None`,
//!    `kube-apiserver` admission webhook immediately rejects the manifest:
//!    `spec.sessionAffinityConfig: Forbidden: must not be set when sessionAffinity is not ClientIP`.
//! 2. When authors provide `sessionAffinityConfig.clientIP`, their explicit intent is Client IP
//!    stickiness. Promoting `sessionAffinity: ClientIP` resolves admission rejection deterministically.
//! 3. Conversely, if `sessionAffinity` is explicitly `None` and an empty or leftover
//!    `sessionAffinityConfig` exists, the orphaned config must be pruned.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_NET_015: &str = "NET-015";

/// Reconciles Service `spec.sessionAffinity` with `spec.sessionAffinityConfig`.
pub fn heal_session_affinity_mismatch(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return changes;
    }

    let svc_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-service".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        let has_config = spec.find_node("sessionAffinityConfig").is_some();
        let current_affinity = spec
            .find_node("sessionAffinity")
            .and_then(|n| n.value.clone());

        if has_config {
            let s_indent = spec.indent;
            match current_affinity {
                None => {
                    // sessionAffinityConfig is present, but sessionAffinity is missing:
                    // promote sessionAffinity: ClientIP
                    spec.children.insert(
                        0,
                        SemanticNode {
                            key: "sessionAffinity".to_string(),
                            value: Some("ClientIP".to_string()),
                            indent: s_indent + 2,
                            is_empty_flow: false,
                            children: Vec::new(),
                            shards: Vec::new(),
                        },
                    );
                    let msg = format!(
                        "Remediation [{}]: Injected 'sessionAffinity: ClientIP' on Service '{}' to satisfy sessionAffinityConfig contract.",
                        RULE_NET_015, svc_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
                Some(ref val) if val.trim().trim_matches(|c| c == '\'' || c == '"').eq_ignore_ascii_case("none") => {
                    // Check if sessionAffinityConfig contains actual clientIP settings
                    let has_client_ip = spec
                        .find_node("sessionAffinityConfig")
                        .and_then(|sac| sac.find_node("clientIP"))
                        .is_some();

                    if has_client_ip {
                        // Explicit clientIP config provided, but sessionAffinity set to None:
                        // promote to ClientIP
                        if let Some(aff_node) = spec.find_node_mut("sessionAffinity") {
                            let old_val = val.clone();
                            aff_node.value = Some("ClientIP".to_string());
                            for s in &mut aff_node.shards {
                                s.value = Some("ClientIP".to_string());
                            }
                            let msg = format!(
                                "Remediation [{}]: Promoted Service '{}' sessionAffinity '{}' -> 'ClientIP' matching defined sessionAffinityConfig.",
                                RULE_NET_015, svc_name, old_val
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    } else {
                        // Empty/orphaned sessionAffinityConfig while sessionAffinity: None -> prune config
                        spec.children.retain(|c| c.key != "sessionAffinityConfig");
                        let msg = format!(
                            "Remediation [{}]: Pruned orphaned 'sessionAffinityConfig' on Service '{}' because sessionAffinity is None.",
                            RULE_NET_015, svc_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
                _ => {}
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_inject_client_ip_when_config_present() {
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
                        value: Some("Service".to_string()),
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
                            value: Some("sticky-svc".to_string()),
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
                            key: "sessionAffinityConfig".to_string(),
                            value: None,
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "clientIP".to_string(),
                                value: None,
                                indent: 4,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "timeoutSeconds".to_string(),
                                    value: Some("3600".to_string()),
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

        let changes = heal_session_affinity_mismatch(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Injected 'sessionAffinity: ClientIP'"));

        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(spec.find_value("sessionAffinity"), Some("ClientIP".to_string()));
    }

    #[test]
    fn test_promote_none_to_client_ip_when_config_has_client_ip() {
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
                        value: Some("Service".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "sessionAffinity".to_string(),
                                value: Some("None".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                            SemanticNode {
                                key: "sessionAffinityConfig".to_string(),
                                value: None,
                                indent: 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "clientIP".to_string(),
                                    value: None,
                                    indent: 4,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "timeoutSeconds".to_string(),
                                        value: Some("1800".to_string()),
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

        let changes = heal_session_affinity_mismatch(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Promoted Service 'unnamed-service' sessionAffinity 'None' -> 'ClientIP'"));

        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(spec.find_value("sessionAffinity"), Some("ClientIP".to_string()));
    }
}
