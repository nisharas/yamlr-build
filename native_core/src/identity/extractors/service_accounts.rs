//! ServiceAccount Extractor
//!
//! Why: Extracts serviceAccountName bindings from workload specifications to verify
//! RBAC identities and ensure non-default service account usage.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct ServiceAccountExtractor;

impl NativeMetadataExtractor for ServiceAccountExtractor {
    fn name(&self) -> &'static str {
        "ServiceAccountExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let paths = iter_shard_paths(shards);
        for (_path, s) in paths {
            let is_sa = s.key.eq_ignore_ascii_case("serviceAccountName")
                || s.key.eq_ignore_ascii_case("serviceAccount");

            if is_sa {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    if !clean.is_empty() {
                        identity.service_account = Some(clean.clone());
                        if !identity
                            .relationships
                            .iter()
                            .any(|r| r.target_kind == "ServiceAccount" && r.target_name == clean)
                        {
                            identity.relationships.push(NativeRelationship {
                                rel_type: RelationshipType::CONSUMES,
                                target_kind: "ServiceAccount".to_string(),
                                target_name: clean,
                                target_namespace: Some(identity.namespace.clone()),
                            });
                        }
                        break;
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_service_account() {
        let raw = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: app\nspec:\n  template:\n    spec:\n      serviceAccountName: app-sa";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Deployment".to_string(),
            name: "app".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        ServiceAccountExtractor.extract(&shards, &mut id);
        assert_eq!(id.service_account, Some("app-sa".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "ServiceAccount" && r.target_name == "app-sa"));
    }
}
