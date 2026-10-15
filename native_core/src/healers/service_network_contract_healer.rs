//! Service Network Contract Healer (Rule NET-016 / Trap 62).
//!
//! Why: In Kubernetes `Service`, `publishNotReadyAddresses` is a boolean field under `spec`.
//! 1. Deprecated annotation: Previously configured via annotation
//!    `service.alpha.kubernetes.io/tolerate-unready-endpoints`.
//! 2. Quoted boolean string: Developers often write `publishNotReadyAddresses: "true"`,
//!    `publishNotReadyAddresses: "false"`, or misplace it under `metadata.annotations`.
//!    The Kubernetes OpenAPI schema requires strict unquoted boolean `true` or `false`.
//! 3. This healer promotes any legacy tolerate-unready annotation to `spec.publishNotReadyAddresses: true`
//!    and unquotes any string boolean literals.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_NET_016: &str = "NET-016";

/// Reconciles `spec.publishNotReadyAddresses` on Services.
pub fn heal_service_publish_not_ready_addresses(
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

    // 1. Check legacy annotation `service.alpha.kubernetes.io/tolerate-unready-endpoints`
    let has_legacy_annot = manifest
        .root
        .find_annotation("service.alpha.kubernetes.io/tolerate-unready-endpoints")
        .map(|v| v.trim().trim_matches(|c| c == '\'' || c == '"').eq_ignore_ascii_case("true"))
        .unwrap_or(false);

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(node) = spec.find_node_mut("publishNotReadyAddresses") {
            if let Some(val) = &node.value {
                let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                let canonical = if clean.eq_ignore_ascii_case("true") {
                    Some("true")
                } else if clean.eq_ignore_ascii_case("false") {
                    Some("false")
                } else {
                    None
                };

                if let Some(canon_bool) = canonical {
                    if val != canon_bool {
                        let old_val = val.clone();
                        node.value = Some(canon_bool.to_string());
                        for s in &mut node.shards {
                            s.value = Some(canon_bool.to_string());
                        }
                        let msg = format!(
                            "Remediation [{}]: Normalized Service '{}' publishNotReadyAddresses '{}' -> '{}'.",
                            RULE_NET_016, svc_name, old_val, canon_bool
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        } else if has_legacy_annot {
            // Promote legacy annotation to spec.publishNotReadyAddresses: true
            let s_indent = spec.indent;
            spec.children.push(SemanticNode {
                key: "publishNotReadyAddresses".to_string(),
                value: Some("true".to_string()),
                indent: s_indent + 2,
                is_empty_flow: false,
                children: Vec::new(),
                shards: Vec::new(),
            });
            let msg = format!(
                "Remediation [{}]: Promoted legacy 'tolerate-unready-endpoints' annotation to 'spec.publishNotReadyAddresses: true' on Service '{}'.",
                RULE_NET_016, svc_name
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
    fn test_unquote_publish_not_ready_addresses() {
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
                            value: Some("headless-db".to_string()),
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
                            key: "publishNotReadyAddresses".to_string(),
                            value: Some("\"true\"".to_string()),
                            indent: 2,
                            is_empty_flow: false,
                            children: Vec::new(),
                            shards: Vec::new(),
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_service_publish_not_ready_addresses(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(spec.find_value("publishNotReadyAddresses"), Some("true".to_string()));
    }
}
