//! Violation Remediation Engine for inline integrity violations.
//!
//! Why: Remediates known integrity rules (REL-003, OPS-002, PRO-001, SEC-002, REL-002, REL-010)
//! cleanly without polluting the main orchestrator loop in healing.rs.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub fn remediate_integrity_violations(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    for violation in manifest.integrity_violations.clone() {
        match violation.rule_id.as_str() {
            "REL-003" => {
                // Scaling War (HPA vs Replicas)
                if let Some(spec) = manifest.root.find_node_mut("spec") {
                    if let Some(idx) = spec.children.iter().position(|c| c.key == "replicas") {
                        spec.children.remove(idx);
                        let msg = "Remediation [REL-003]: Removed hardcoded 'replicas' to allow HPA scaling.".to_string();
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
            "OPS-002" => {
                // Floating Tag (Change latest to stable if possible)
                for container in manifest.root.find_nodes_by_key_recursive_mut("image") {
                    let mut needs_update = None;
                    if let Some(val) = &container.value {
                        let clean_val = val.trim_matches('"').trim_matches('\'');
                        if clean_val.ends_with(":latest") {
                            needs_update =
                                Some((val.clone(), clean_val.replace(":latest", ":stable-pinned")));
                        }
                    }
                    if let Some((old_val, new_val)) = needs_update {
                        container.value = Some(new_val.clone());
                        for s in &mut container.shards {
                            s.value = Some(new_val.clone());
                        }
                        let msg = format!(
                            "Remediation [OPS-002]: Pinned image '{}' to stable digest-simulation.",
                            old_val
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
            "PRO-001" => {
                // API Deprecation & Multi-Version Migration
                let dep_changes = crate::healers::api_deprecation_healer::heal_api_deprecations(
                    manifest, telemetry,
                );
                changes.extend(dep_changes);
            }
            "SEC-002" => {
                // Image Pull Policy
                for container in manifest
                    .root
                    .find_nodes_by_key_recursive_mut("imagePullPolicy")
                {
                    if container.value.as_deref() != Some("Always") {
                        container.value = Some("Always".to_string());
                        let msg = "Remediation [SEC-002]: Enforced 'imagePullPolicy: Always' on container.".to_string();
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
            "REL-002" => {
                // Ingress PathType & Service Port Realignment
                let kind = manifest.root.find_value("kind").unwrap_or_default();
                if kind == "Ingress" {
                    if let Some(spec) = manifest.root.find_node_mut("spec") {
                        for path_node in spec.find_nodes_by_key_recursive_mut("paths") {
                            for child in &mut path_node.children {
                                if child.find_value("pathType").is_none() {
                                    child.children.push(SemanticNode {
                                        key: "pathType".to_string(),
                                        value: Some("Prefix".to_string()),
                                        children: Vec::new(),
                                        shards: Vec::new(),
                                        indent: child.indent + 2,
                                        is_empty_flow: false,
                                    });
                                    let msg = "Remediation [REL-002]: Injected required 'pathType: Prefix' for Ingress v1.".to_string();
                                    native_record_healing_impact(telemetry, &msg);
                                    changes.push(msg);
                                }
                            }
                        }
                    }
                }
            }
            "REL-010" => {
                // Pod Selector and MatchLabels Synchronization
                let kind = manifest.root.find_value("kind").unwrap_or_default();
                if kind == "Deployment" || kind == "StatefulSet" || kind == "DaemonSet" {
                    if let Some(spec) = manifest.root.find_node_mut("spec") {
                        if let Some(template) = spec.find_node_mut("template") {
                            if let Some(tmpl_meta) = template.find_node_mut("metadata") {
                                if let Some(tmpl_labels) = tmpl_meta.find_node_mut("labels") {
                                    if let Some(app_label) = tmpl_labels.find_value("app") {
                                        if let Some(selector) = spec.find_node_mut("selector") {
                                            if let Some(match_labels) =
                                                selector.find_node_mut("matchLabels")
                                            {
                                                if match_labels.find_value("app").as_deref()
                                                    != Some(&app_label)
                                                {
                                                    if let Some(app_node) =
                                                        match_labels.find_node_mut("app")
                                                    {
                                                        app_node.value = Some(app_label.clone());
                                                        let msg = format!("Remediation [REL-010]: Realigned selector matchLabel 'app: {}' with template labels.", app_label);
                                                        native_record_healing_impact(
                                                            telemetry, &msg,
                                                        );
                                                        changes.push(msg);
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
            _ => {}
        }
    }
    changes
}
