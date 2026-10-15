//! ClusterRoleBinding Extractor
//!
//! Why: Extracts roleRef and subjects for ClusterRoleBindings to model RBAC authorization
//! graphs and identify orphaned or broken cluster role references.
//! Handles arbitrary key ordering in roleRef and subjects list items.

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

        let mut role_name: Option<String> = None;

        let flush_role_ref = |name: &mut Option<String>, id: &mut NativeIdentity| {
            if let Some(n) = name.take() {
                if !n.is_empty() {
                    if !id.cluster_role_refs.contains(&n) {
                        id.cluster_role_refs.push(n.clone());
                    }
                    id.relationships.push(NativeRelationship {
                        rel_type: RelationshipType::BINDS,
                        target_kind: "ClusterRole".to_string(),
                        target_name: n,
                        target_namespace: None,
                    });
                }
            }
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
                flush_role_ref(&mut role_name, identity);
                flush_subject(&mut subject_kind, &mut subject_name, &mut subject_ns, identity);
                in_role_ref = true;
                role_ref_indent = s.indent;
                in_subjects = false;
                continue;
            }
            if s.key == "subjects" && s.value.is_none() {
                flush_role_ref(&mut role_name, identity);
                flush_subject(&mut subject_kind, &mut subject_name, &mut subject_ns, identity);
                in_subjects = true;
                subjects_indent = s.indent;
                in_role_ref = false;
                continue;
            }

            if in_role_ref {
                if s.indent <= role_ref_indent && !s.is_list_item && !s.key.is_empty() {
                    flush_role_ref(&mut role_name, identity);
                    in_role_ref = false;
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
        flush_role_ref(&mut role_name, identity);
        flush_subject(&mut subject_kind, &mut subject_name, &mut subject_ns, identity);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_cluster_role_binding_arbitrary_key_ordering() {
        // Name before kind in subjects, namespace before name
        let raw = r#"
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-binding
roleRef:
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
subjects:
- namespace: kube-system
  name: deployer
  kind: ServiceAccount
- name: global-admin
  kind: User
"#;
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
        assert!(id.relationships.iter().any(|r| r.target_kind == "ServiceAccount"
            && r.target_name == "deployer"
            && r.target_namespace == Some("kube-system".to_string())));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "User" && r.target_name == "global-admin"));
    }
}
