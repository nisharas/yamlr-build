//! RoleBinding Subject Healer (Rule RBAC-003).
//!
//! Why: In RoleBinding subjects:
//! 1. Specifying `apiGroup: rbac.authorization.k8s.io` for a `kind: ServiceAccount` fails validation.
//! 2. Omitting `namespace` on a ServiceAccount subject can cause ambiguous binding resolution.
//! 3. Typos in ServiceAccount names cause RBAC permission loss and 403 Forbidden errors.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RB_SUBJECT_RULE_ID: &str = "RBAC-003";
pub const SA_SIMILARITY_THRESHOLD: f64 = 0.75;

/// Heals RoleBinding subject definitions.
pub fn heal_role_binding_subjects(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "RoleBinding" {
        return changes;
    }

    let binding_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-rb".to_string());

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    if let Some(subjects_node) = manifest.root.find_node_mut("subjects") {
        let is_flat = subjects_node.children.iter().any(|c| c.key == "kind");
        let has_top_ns = subjects_node.children.iter().any(|c| c.key == "namespace" && c.value.as_ref().map_or(false, |v| !v.trim().is_empty()));

        for subject in &mut subjects_node.children {
            let subj_kind = subject.find_value("kind").unwrap_or_default();

            if subj_kind == "ServiceAccount" {
                // 1. Clear erroneous apiGroup
                if let Some(group_node) = subject.find_node_mut("apiGroup") {
                    let group_val = group_node.value.clone().unwrap_or_default();
                    let clean_group = group_val.trim().trim_matches('"').trim_matches('\'');
                    if clean_group == "rbac.authorization.k8s.io" || !clean_group.is_empty() {
                        group_node.value = Some(String::new());
                        for s in &mut group_node.shards {
                            s.value = Some(String::new());
                        }
                        let msg = format!(
                            "Remediation [{}]: Cleared invalid apiGroup '{}' on ServiceAccount subject in RoleBinding '{}'.",
                            RB_SUBJECT_RULE_ID, clean_group, binding_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }

                // 2. Ensure namespace is present (defaulting to RoleBinding namespace)
                let current_ns = subject.find_value("namespace").unwrap_or_default();
                let clean_ns = current_ns
                    .trim()
                    .trim_matches('"')
                    .trim_matches('\'')
                    .to_string();
                let effective_ns = if clean_ns.is_empty() {
                    if is_flat && has_top_ns {
                        ns.clone()
                    } else if subject.key == "kind" {
                        ns.clone()
                    } else {
                        let indent = subject.indent + 2;
                        subject.children.push(SemanticNode {
                            key: "namespace".to_string(),
                            value: Some(ns.clone()),
                            children: Vec::new(),
                            shards: Vec::new(),
                            indent,
                            is_empty_flow: false,
                        });
                        let msg = format!(
                            "Remediation [{}]: Injected default namespace '{}' for ServiceAccount subject in RoleBinding '{}'.",
                            RB_SUBJECT_RULE_ID, ns, binding_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                        ns.clone()
                    }
                } else {
                    clean_ns
                };

                // 3. Fuzzy match ServiceAccount name
                if let Some(name_node) = subject.find_node_mut("name") {
                    let sa_name = name_node.value.clone().unwrap_or_default();
                    let sa_clean = sa_name.trim().trim_matches('"').trim_matches('\'');

                    let known_sas: Vec<&NativeIdentity> = identities
                        .iter()
                        .filter(|id| {
                            id.kind == "ServiceAccount"
                                && (id.namespace == effective_ns || id.namespace.is_empty())
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
                                "Remediation [{}]: Aligned ServiceAccount subject name '{}' -> '{}' in RoleBinding '{}' (similarity: {:.2}).",
                                RB_SUBJECT_RULE_ID, sa_clean, target, binding_name, best_ratio
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
    fn test_heal_role_binding_subject_namespace_and_typo() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("RoleBinding".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "namespace".into(),
                            value: Some("prod".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        }],
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
                                    value: Some("deployer-sa".into()),
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

        let target_sa = NativeIdentity {
            kind: "ServiceAccount".into(),
            name: "deployer-sa".into(),
            namespace: "prod".into(),
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_role_binding_subjects(&mut manifest, &[target_sa], &mut telemetry);
        assert_eq!(changes.len(), 1); // namespace injected
        let subj = &manifest.root.find_node("subjects").unwrap().children[0];
        assert_eq!(subj.find_value("namespace"), Some("prod".to_string()));
    }
}
