//! RoleBinding Extractor
//!
//! Why: Extracts roleRef and subjects for namespace-scoped RoleBindings to model
//! RBAC authorization DAGs and detect missing Roles or ServiceAccounts.
//! Handles arbitrary key ordering in roleRef and subjects list items.

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

        let mut role_kind: Option<String> = None;
        let mut role_name: Option<String> = None;

        let flush_role_ref =
            |kind: &mut Option<String>, name: &mut Option<String>, id: &mut NativeIdentity| {
                if let Some(n) = name.take() {
                    if !n.is_empty() {
                        if !id.role_refs.contains(&n) {
                            id.role_refs.push(n.clone());
                        }
                        let k = kind.take().unwrap_or_else(|| "Role".to_string());
                        id.relationships.push(NativeRelationship {
                            rel_type: RelationshipType::BINDS,
                            target_kind: k,
                            target_name: n,
                            target_namespace: Some(id.namespace.clone()),
                        });
                    }
                }
                *kind = None;
            };

        let mut subject_kind: Option<String> = None;
        let mut subject_name: Option<String> = None;
        let mut subject_ns: Option<String> = None;

        let flush_subject = |kind: &mut Option<String>,
                             name: &mut Option<String>,
                             ns: &mut Option<String>,
                             id: &mut NativeIdentity| {
            if let Some(n) = name.take() {
                if !n.is_empty() {
                    let k = kind.take().unwrap_or_else(|| "ServiceAccount".to_string());
                    id.relationships.push(NativeRelationship {
                        rel_type: RelationshipType::BINDS,
                        target_kind: k,
                        target_name: n,
                        target_namespace: ns.take(),
                    });
                }
            }
            *kind = None;
            *ns = None;
        };

        for s in shards {
            if s.key == "roleRef" && s.value.is_none() {
                flush_role_ref(&mut role_kind, &mut role_name, identity);
                flush_subject(&mut subject_kind, &mut subject_name, &mut subject_ns, identity);
                in_role_ref = true;
                role_ref_indent = s.indent;
                in_subjects = false;
                continue;
            }
            if s.key == "subjects" && s.value.is_none() {
                flush_role_ref(&mut role_kind, &mut role_name, identity);
                flush_subject(&mut subject_kind, &mut subject_name, &mut subject_ns, identity);
                in_subjects = true;
                subjects_indent = s.indent;
                in_role_ref = false;
                continue;
            }

            if in_role_ref {
                if s.indent <= role_ref_indent && !s.is_list_item && !s.key.is_empty() {
                    flush_role_ref(&mut role_kind, &mut role_name, identity);
                    in_role_ref = false;
                } else if s.key == "kind" {
                    if let Some(val) = &s.value {
                        role_kind = Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
                    }
                } else if s.key == "name" {
                    if let Some(val) = &s.value {
                        role_name = Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
                    }
                }
            } else if in_subjects {
                if s.indent <= subjects_indent && !s.is_list_item && !s.key.is_empty() {
                    flush_subject(&mut subject_kind, &mut subject_name, &mut subject_ns, identity);
                    in_subjects = false;
                } else {
                    if s.is_list_item {
                        flush_subject(
                            &mut subject_kind,
                            &mut subject_name,
                            &mut subject_ns,
                            identity,
                        );
                    }
                    if s.key == "kind" {
                        if let Some(val) = &s.value {
                            subject_kind =
                                Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
                        }
                    } else if s.key == "name" {
                        if let Some(val) = &s.value {
                            subject_name =
                                Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
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
        flush_role_ref(&mut role_kind, &mut role_name, identity);
        flush_subject(&mut subject_kind, &mut subject_name, &mut subject_ns, identity);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_role_binding_arbitrary_key_ordering() {
        // Name before kind in roleRef, and name before kind in subjects
        let raw = r#"
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-rb
  namespace: default
roleRef:
  name: admin-cluster-role
  kind: ClusterRole
  apiGroup: rbac.authorization.k8s.io
subjects:
- name: app-sa
  kind: ServiceAccount
- namespace: kube-system
  name: backend-user
  kind: User
"#;
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "RoleBinding".to_string(),
            name: "app-rb".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        RoleBindingExtractor.extract(&shards, &mut id);
        assert!(id.role_refs.contains(&"admin-cluster-role".to_string()));
        assert!(id.relationships.iter().any(|r| r.target_kind == "ClusterRole"
            && r.target_name == "admin-cluster-role"));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "ServiceAccount" && r.target_name == "app-sa"));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "User" && r.target_name == "backend-user"));
    }
}
