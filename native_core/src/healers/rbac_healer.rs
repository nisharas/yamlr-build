//! RBAC Role & ServiceAccount Typo Healer (Feature 6 of 15).
//!
//! Why: Typos in RBAC `roleRef` or `subjects` (e.g. `roleRef.name: pod-readr` vs
//! `Role: pod-reader`) are insidious security failures. Kubernetes applies the
//! binding without error, but grants 0 permissions, causing silent 403 Forbidden
//! outages in production pods.
//!
//! This module resolves:
//! 1. `RoleBinding` / `ClusterRoleBinding` `roleRef.name` fuzzy repair.
//! 2. `subjects` ServiceAccount `name` fuzzy repair.
//! 3. Workload `spec.serviceAccountName` fuzzy repair.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub static RBAC_SIMILARITY_THRESHOLD: f64 = 0.75;

/// Aligns a roleRef node against known available roles.
pub fn align_role_ref_node(
    role_ref: &mut SemanticNode,
    roles: &[&NativeIdentity],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
    binding_name: &str,
) -> bool {
    let current_name = match role_ref.find_value("name") {
        Some(n) => n,
        None => return false,
    };
    let ref_kind = role_ref
        .find_value("kind")
        .unwrap_or_else(|| "ClusterRole".to_string());

    // Check if already matches
    if roles
        .iter()
        .any(|r| r.kind == ref_kind && r.name == current_name)
    {
        return false;
    }

    // Find best fuzzy match
    let mut best_target = None;
    let mut best_ratio = 0.0;

    for r in roles {
        if r.kind == ref_kind {
            let ratio = crate::healers::selector_healer::similarity_ratio(&current_name, &r.name);
            if ratio >= RBAC_SIMILARITY_THRESHOLD && ratio > best_ratio {
                best_ratio = ratio;
                best_target = Some(r);
            }
        }
    }

    if let Some(target) = best_target {
        if let Some(name_node) = role_ref.find_node_mut("name") {
            name_node.value = Some(target.name.clone());
            for s in &mut name_node.shards {
                s.value = Some(target.name.clone());
            }
            let msg = format!(
                "Remediation [SEC-004]: Aligned RBAC roleRef in '{}' from '{}' -> '{}' ({}) (similarity: {:.2}).",
                binding_name, current_name, target.name, target.kind, best_ratio
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
            return true;
        }
    }

    false
}

/// Aligns ServiceAccount subjects in a RoleBinding against known ServiceAccounts.
pub fn align_subjects_node(
    subjects_node: &mut SemanticNode,
    sas: &[&NativeIdentity],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
    binding_name: &str,
) -> bool {
    let mut modified = false;

    for subject in &mut subjects_node.children {
        let kind = subject.find_value("kind").unwrap_or_default();
        if kind != "ServiceAccount" {
            continue;
        }

        let current_name = match subject.find_value("name") {
            Some(n) => n,
            None => continue,
        };

        if sas.iter().any(|s| s.name == current_name) {
            continue;
        }

        // Fuzzy match
        let mut best_target = None;
        let mut best_ratio = 0.0;

        for s in sas {
            let ratio = crate::healers::selector_healer::similarity_ratio(&current_name, &s.name);
            if ratio >= RBAC_SIMILARITY_THRESHOLD && ratio > best_ratio {
                best_ratio = ratio;
                best_target = Some(s);
            }
        }

        if let Some(target) = best_target {
            if let Some(name_node) = subject.find_node_mut("name") {
                name_node.value = Some(target.name.clone());
                for s in &mut name_node.shards {
                    s.value = Some(target.name.clone());
                }
                let msg = format!(
                    "Remediation [SEC-004]: Aligned ServiceAccount subject in '{}' from '{}' -> '{}' (similarity: {:.2}).",
                    binding_name, current_name, target.name, best_ratio
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
                modified = true;
            }
        }
    }

    modified
}

/// Primary Entrypoint: Aligns RBAC roleRef, subjects, and workload serviceAccountName.
pub fn heal_rbac_references(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    let binding_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unknown".to_string());
    let binding_ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    if kind == "RoleBinding" || kind == "ClusterRoleBinding" {
        // Collect available roles
        let available_roles: Vec<&NativeIdentity> = identities
            .iter()
            .filter(|id| {
                if id.kind == "ClusterRole" {
                    true
                } else if id.kind == "Role" {
                    kind == "RoleBinding" && id.namespace == binding_ns
                } else {
                    false
                }
            })
            .collect();

        // Collect available service accounts
        let available_sas: Vec<&NativeIdentity> = identities
            .iter()
            .filter(|id| {
                id.kind == "ServiceAccount"
                    && (kind == "ClusterRoleBinding" || id.namespace == binding_ns)
            })
            .collect();

        if let Some(role_ref) = manifest.root.find_node_mut("roleRef") {
            align_role_ref_node(
                role_ref,
                &available_roles,
                telemetry,
                &mut changes,
                &binding_name,
            );
        }

        if let Some(subjects) = manifest.root.find_node_mut("subjects") {
            align_subjects_node(
                subjects,
                &available_sas,
                telemetry,
                &mut changes,
                &binding_name,
            );
        }
    } else if crate::healers::selector_healer::WORKLOAD_KINDS.contains(&kind.as_str()) {
        // Workload serviceAccountName fuzzy repair
        let available_sas: Vec<&NativeIdentity> = identities
            .iter()
            .filter(|id| id.kind == "ServiceAccount" && id.namespace == binding_ns)
            .collect();

        if !available_sas.is_empty() {
            for sa_node in manifest
                .root
                .find_nodes_by_key_recursive_mut("serviceAccountName")
            {
                let current_sa = match sa_node.value.clone() {
                    Some(s) => s,
                    None => continue,
                };
                if !available_sas.iter().any(|s| s.name == current_sa) {
                    let mut best_target = None;
                    let mut best_ratio = 0.0;
                    for s in &available_sas {
                        let ratio =
                            crate::healers::selector_healer::similarity_ratio(&current_sa, &s.name);
                        if ratio >= RBAC_SIMILARITY_THRESHOLD && ratio > best_ratio {
                            best_ratio = ratio;
                            best_target = Some(s);
                        }
                    }
                    if let Some(target) = best_target {
                        sa_node.value = Some(target.name.clone());
                        for shard in &mut sa_node.shards {
                            shard.value = Some(target.name.clone());
                        }
                        let msg = format!(
                            "Remediation [SEC-004]: Aligned workload serviceAccountName in '{}' from '{}' -> '{}'.",
                            binding_name, current_sa, target.name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
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
    fn test_align_role_ref() {
        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();

        let mut role_ref = SemanticNode {
            key: "roleRef".to_string(),
            value: None,
            indent: 0,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![
                SemanticNode {
                    key: "kind".to_string(),
                    value: Some("ClusterRole".to_string()),
                    indent: 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
                SemanticNode {
                    key: "name".to_string(),
                    value: Some("view-readr".to_string()), // Typo for view-reader
                    indent: 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
            ],
        };

        let target_role = NativeIdentity {
            kind: "ClusterRole".to_string(),
            api_version: Some("rbac.authorization.k8s.io/v1".to_string()),
            name: "view-reader".to_string(),
            namespace: "__cluster_scoped__".to_string(),
            owner_refs: Vec::new(),
            labels: std::collections::HashMap::new(),
            selector: std::collections::HashMap::new(),
            config_refs: Vec::new(),
            secret_refs: Vec::new(),
            volume_refs: Vec::new(),
            service_refs: Vec::new(),
            role_refs: Vec::new(),
            cluster_role_refs: Vec::new(),
            service_account: None,
            shadow_fingerprint: String::new(),
            relationships: Vec::new(),
            ports: Vec::new(),
            ..Default::default()
        };

        let roles = vec![&target_role];
        let modified = align_role_ref_node(
            &mut role_ref,
            &roles,
            &mut telemetry,
            &mut changes,
            "test-binding",
        );
        assert!(modified);
        assert_eq!(role_ref.find_value("name"), Some("view-reader".to_string()));
    }
}
