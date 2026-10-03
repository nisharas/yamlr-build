//! ClusterRoleBinding Extractor
//!
//! Why: Extracts roleRef and subjects for ClusterRoleBindings to model RBAC authorization
//! graphs and identify orphaned or broken cluster role references.

use super::NativeMetadataExtractor;
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct ClusterRoleBindingExtractor;

impl NativeMetadataExtractor for ClusterRoleBindingExtractor {
    fn name(&self) -> &'static str {
        "ClusterRoleBindingExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "ClusterRoleBinding" {
            return;
        }

        let mut in_role_ref = false;
        let mut role_ref_indent = 0;
        let mut in_subjects = false;
        let mut subjects_indent = 0;

        let mut subject_kind = String::new();
        let mut subject_name = String::new();
        let mut subject_ns: Option<String> = None;

        for s in shards {
            if s.key == "roleRef" && s.value.is_none() {
                in_role_ref = true;
                role_ref_indent = s.indent;
                in_subjects = false;
                continue;
            }
            if s.key == "subjects" && s.value.is_none() {
                in_subjects = true;
                subjects_indent = s.indent;
                in_role_ref = false;
                continue;
            }

            if in_role_ref {
                if s.indent <= role_ref_indent && !s.is_list_item && !s.key.is_empty() {
                    in_role_ref = false;
                } else if s.key == "name" {
                    if let Some(val) = &s.value {
                        let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                        if !identity.cluster_role_refs.contains(&clean) {
                            identity.cluster_role_refs.push(clean.clone());
                        }
                        identity.relationships.push(NativeRelationship {
                            rel_type: RelationshipType::BINDS,
                            target_kind: "ClusterRole".to_string(),
                            target_name: clean,
                            target_namespace: None,
                        });
                    }
                }
            } else if in_subjects {
                if s.indent <= subjects_indent && !s.is_list_item && !s.key.is_empty() {
                    in_subjects = false;
                } else {
                    if s.is_list_item && !subject_name.is_empty() {
                        identity.relationships.push(NativeRelationship {
                            rel_type: RelationshipType::BINDS,
                            target_kind: if subject_kind.is_empty() {
                                "ServiceAccount".to_string()
                            } else {
                                subject_kind.clone()
                            },
                            target_name: subject_name.clone(),
                            target_namespace: subject_ns.clone(),
                        });
                        subject_name.clear();
                        subject_ns = None;
                    }
                    if s.key == "kind" {
                        if let Some(val) = &s.value {
                            subject_kind = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                        }
                    } else if s.key == "name" {
                        if let Some(val) = &s.value {
                            subject_name = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                        }
                    } else if s.key == "namespace" {
                        if let Some(val) = &s.value {
                            subject_ns =
                                Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
                        }
                    }
                }
            }
        }

        if !subject_name.is_empty() {
            identity.relationships.push(NativeRelationship {
                rel_type: RelationshipType::BINDS,
                target_kind: if subject_kind.is_empty() {
                    "ServiceAccount".to_string()
                } else {
                    subject_kind
                },
                target_name: subject_name,
                target_namespace: subject_ns,
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_cluster_role_binding() {
        let raw = "apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRoleBinding\nmetadata:\n  name: admin-binding\nroleRef:\n  apiGroup: rbac.authorization.k8s.io\n  kind: ClusterRole\n  name: cluster-admin\nsubjects:\n- kind: ServiceAccount\n  name: deployer\n  namespace: default";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "ClusterRoleBinding".to_string(),
            name: "admin-binding".to_string(),
            ..Default::default()
        };
        ClusterRoleBindingExtractor.extract(&shards, &mut id);
        assert!(id.cluster_role_refs.contains(&"cluster-admin".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "ClusterRole" && r.target_name == "cluster-admin"));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "ServiceAccount" && r.target_name == "deployer"));
    }
}
