//! PersistentVolumeClaim Reference Extractor
//!
//! Why: Extracts PVC volume mounts to track storage dependencies and detect
//! unbacked volume claims.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct PvcRefExtractor;

impl NativeMetadataExtractor for PvcRefExtractor {
    fn name(&self) -> &'static str {
        "PvcRefExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let paths = iter_shard_paths(shards);
        for (path, s) in paths {
            let is_pvc = (path.contains("persistentVolumeClaim") && s.key == "claimName")
                || (path.contains("volumes") && s.key.eq_ignore_ascii_case("claimName"));

            if is_pvc {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    if !clean.is_empty() && !identity.volume_refs.contains(&clean) {
                        identity.volume_refs.push(clean.clone());
                    }
                    if !clean.is_empty()
                        && !identity.relationships.iter().any(|r| {
                            r.target_kind == "PersistentVolumeClaim" && r.target_name == clean
                        })
                    {
                        identity.relationships.push(NativeRelationship {
                            rel_type: RelationshipType::MOUNTS,
                            target_kind: "PersistentVolumeClaim".to_string(),
                            target_name: clean,
                            target_namespace: Some(identity.namespace.clone()),
                        });
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
    fn test_extract_pvc_refs() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: db-pod\nspec:\n  volumes:\n  - name: data\n    persistentVolumeClaim:\n      claimName: mysql-pvc";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "db-pod".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        PvcRefExtractor.extract(&shards, &mut id);
        assert!(id.volume_refs.contains(&"mysql-pvc".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.rel_type == RelationshipType::MOUNTS && r.target_name == "mysql-pvc"));
    }
}
