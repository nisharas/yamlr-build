//! Namespace Extractor & Scope Normalizer
//!
//! Why: Normalizes resource namespaces with strict distinction between namespaced
//! resources (defaulting to 'default') and cluster-scoped resources ('__cluster_scoped__').

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeShard};

pub struct NamespaceExtractor;

impl NativeMetadataExtractor for NamespaceExtractor {
    fn name(&self) -> &'static str {
        "NamespaceExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let cluster_scoped_kinds = [
            "ClusterRole",
            "ClusterRoleBinding",
            "Namespace",
            "Node",
            "PersistentVolume",
            "StorageClass",
            "CustomResourceDefinition",
        ];

        if cluster_scoped_kinds.contains(&identity.kind.as_str()) {
            identity.namespace = "__cluster_scoped__".to_string();
            return;
        }

        let paths = iter_shard_paths(shards);
        let mut found_ns = None;
        for (path, s) in paths {
            if path == "metadata.namespace" {
                if let Some(val) = &s.value {
                    found_ns = Some(
                        val.trim_matches(|c| c == '"' || c == '\'')
                            .trim()
                            .to_string(),
                    );
                    break;
                }
            }
        }

        if let Some(ns) = found_ns {
            if !ns.is_empty() {
                identity.namespace = ns;
                return;
            }
        }

        if identity.namespace.is_empty() {
            identity.namespace = "default".to_string();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_cluster_scoped_namespace() {
        let raw =
            "apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRole\nmetadata:\n  name: admin";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "ClusterRole".to_string(),
            name: "admin".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        NamespaceExtractor.extract(&shards, &mut id);
        assert_eq!(id.namespace, "__cluster_scoped__");
    }

    #[test]
    fn test_extract_explicit_namespace() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: pod\n  namespace: staging";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "pod".to_string(),
            ..Default::default()
        };
        NamespaceExtractor.extract(&shards, &mut id);
        assert_eq!(id.namespace, "staging");
    }
}
