//! RoleBinding Extractor
//!
//! Why: Extracts roleRef and subjects for namespace-scoped RoleBindings to model
//! RBAC authorization DAGs and detect missing Roles or ServiceAccounts.

use super::NativeMetadataExtractor;
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct RoleBindingExtractor;

impl NativeMetadataExtractor for RoleBindingExtractor {
    fn name(&self) -> &'static str {
        "RoleBindingExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "RoleBinding" {
            return;
        }

        let mut in_role_ref = false;
        let mut role_ref_indent = 0;
        let mut in_subjects = false;
        let mut subjects_indent = 0;

        let mut role_kind = "Role".to_string();
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
                } else if s.key == "kind" {
                    if let Some(val) = &s.value {
                        role_kind = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    }
                } else if s.key == "name" {
                    if let Some(val) = &s.value {
                        let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                        if !identity.role_refs.contains(&clean) {
                            identity.role_refs.push(clean.clone());
                        }
                        identity.relationships.push(NativeRelationship {
                            rel_type: RelationshipType::BINDS,
                            target_kind: role_kind.clone(),
                            target_name: clean,
                            target_namespace: Some(identity.namespace.clone()),
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
    fn test_extract_role_binding() {
        let raw = "apiVersion: rbac.authorization.k8s.io/v1\nkind: RoleBinding\nmetadata:\n  name: app-rb\n  namespace: default\nroleRef:\n  apiGroup: rbac.authorization.k8s.io\n  kind: Role\n  name: pod-reader\nsubjects:\n- kind: ServiceAccount\n  name: app-sa";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "RoleBinding".to_string(),
            name: "app-rb".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        RoleBindingExtractor.extract(&shards, &mut id);
        assert!(id.role_refs.contains(&"pod-reader".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "Role" && r.target_name == "pod-reader"));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "ServiceAccount" && r.target_name == "app-sa"));
    }
}
