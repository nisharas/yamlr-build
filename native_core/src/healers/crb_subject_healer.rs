//! ClusterRoleBinding Subject Healer (Rule RBAC-002).
//!
//! Why: In ClusterRoleBinding subjects:
//! 1. Specifying `apiGroup: rbac.authorization.k8s.io` on a `kind: ServiceAccount` causes
//!    apiserver validation rejection (ServiceAccounts live in the core group `""`).
//! 2. Omitting `namespace` on a ServiceAccount in a cluster-scoped binding breaks binding resolution.
//! 3. Typos in ServiceAccount names cause RBAC privilege dropping.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const CRB_SUBJECT_RULE_ID: &str = "RBAC-002";
pub const SA_SIMILARITY_THRESHOLD: f64 = 0.75;

/// Heals ClusterRoleBinding subject definitions (ServiceAccounts, Namespaces, Groups).
pub fn heal_cluster_role_binding_subjects(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "ClusterRoleBinding" {
        return changes;
    }

    let binding_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-crb".to_string());

    if let Some(subjects_node) = manifest.root.find_node_mut("subjects") {
        let is_flat = subjects_node.children.iter().any(|c| c.key == "kind");
        let has_top_ns = subjects_node.children.iter().any(|c| c.key == "namespace" && c.value.as_ref().map_or(false, |v| !v.trim().is_empty()));

        for subject in &mut subjects_node.children {
            let subj_kind = subject.find_value("kind").unwrap_or_default();

            if subj_kind == "ServiceAccount" {
                // 1. Check and heal erroneous apiGroup
                if let Some(group_node) = subject.find_node_mut("apiGroup") {
                    let group_val = group_node.value.clone().unwrap_or_default();
                    let clean_group = group_val.trim().trim_matches('"').trim_matches('\'');
                    if clean_group == "rbac.authorization.k8s.io" || !clean_group.is_empty() {
                        group_node.value = Some(String::new());
                        for s in &mut group_node.shards {
                            s.value = Some(String::new());
                        }
                        let msg = format!(
                            "Remediation [{}]: Cleared invalid apiGroup '{}' on ServiceAccount subject in ClusterRoleBinding '{}'.",
                            CRB_SUBJECT_RULE_ID, clean_group, binding_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }

                // 2. Check and inject missing namespace
                let current_ns = subject.find_value("namespace").unwrap_or_default();
                let ns_clean = current_ns
                    .trim()
                    .trim_matches('"')
                    .trim_matches('\'')
                    .to_string();
                if ns_clean.is_empty() {
                    if is_flat && has_top_ns {
                        // Namespace is already present on the flat subjects block
                    } else if subject.key == "kind" {
                        // Do not nest namespace under scalar kind node
                    } else {
                        let indent = subject.indent + 2;
                        subject.children.push(SemanticNode {
                            key: "namespace".to_string(),
                            value: Some("default".to_string()),
                            children: Vec::new(),
                            shards: Vec::new(),
                            indent,
                            is_empty_flow: false,
                        });
                        let msg = format!(
                            "Remediation [{}]: Injected missing 'namespace: default' for ServiceAccount subject in ClusterRoleBinding '{}'.",
                            CRB_SUBJECT_RULE_ID, binding_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }

                // 3. Check and fuzzy-heal ServiceAccount name
                let target_ns = if ns_clean.is_empty() {
                    "default"
                } else {
                    &ns_clean
                };
                if let Some(name_node) = subject.find_node_mut("name") {
                    let sa_name = name_node.value.clone().unwrap_or_default();
                    let sa_clean = sa_name.trim().trim_matches('"').trim_matches('\'');

                    let known_sas: Vec<&NativeIdentity> = identities
                        .iter()
                        .filter(|id| {
                            id.kind == "ServiceAccount"
                                && (id.namespace == target_ns || id.namespace.is_empty())
                        })
                        .collect();

                    if !sa_clean.is_empty()
                        && !known_sas.iter().any(|sa| sa.name == sa_clean)
                        && !known_sas.is_empty()
                    {
                        let mut best_target = None;
                        let mut best_ratio = 0.0;
                        for sa in known_sas {
                            let ratio = crate::healers::selector_healer::similarity_ratio(
                                sa_clean, &sa.name,
                            );
                            if ratio >= SA_SIMILARITY_THRESHOLD && ratio > best_ratio {
                                best_ratio = ratio;
                                best_target = Some(sa.name.clone());
                            }
                        }

                        if let Some(target) = best_target {
                            name_node.value = Some(target.clone());
                            for s in &mut name_node.shards {
                                s.value = Some(target.clone());
                            }
                            let msg = format!(
                                "Remediation [{}]: Aligned ServiceAccount subject name '{}' -> '{}' in ClusterRoleBinding '{}' (similarity: {:.2}).",
                                CRB_SUBJECT_RULE_ID, sa_clean, target, binding_name, best_ratio
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

    #[test]
    fn test_heal_crb_invalid_apigroup_and_missing_ns() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("ClusterRoleBinding".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "subjects".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "-".into(),
                            value: None,
                            children: vec![
                                SemanticNode {
                                    key: "kind".into(),
                                    value: Some("ServiceAccount".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                },
                                SemanticNode {
                                    key: "name".into(),
                                    value: Some("my-sa".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                },
                                SemanticNode {
                                    key: "apiGroup".into(),
                                    value: Some("rbac.authorization.k8s.io".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                },
                            ],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        }],
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
        let changes = heal_cluster_role_binding_subjects(&mut manifest, &[], &mut telemetry);
        assert_eq!(changes.len(), 2); // apiGroup cleared and namespace injected
        let subj = &manifest.root.find_node("subjects").unwrap().children[0];
        assert_eq!(subj.find_value("apiGroup"), Some("".to_string()));
        assert_eq!(subj.find_value("namespace"), Some("default".to_string()));
    }
}
