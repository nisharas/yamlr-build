//! Secret Reference Extractor
//!
//! Why: Extracts Secret dependencies across envFrom, secretKeyRef, and volume
//! mounts to detect missing credentials or unpinned secret references.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct SecretRefExtractor;

impl NativeMetadataExtractor for SecretRefExtractor {
    fn name(&self) -> &'static str {
        "SecretRefExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let paths = iter_shard_paths(shards);
        for (path, s) in paths {
            let is_secret_ref = (path.contains("secretKeyRef") && s.key == "name")
                || (path.contains("secretRef") && s.key == "name")
                || (path.contains("volumes") && path.contains("secret") && s.key == "secretName")
                || (s.key.eq_ignore_ascii_case("secretName")
                    || s.key.eq_ignore_ascii_case("secretRef"));

            if is_secret_ref {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    if !clean.is_empty() && !identity.secret_refs.contains(&clean) {
                        identity.secret_refs.push(clean.clone());
                    }
                    if !clean.is_empty()
                        && !identity
                            .relationships
                            .iter()
                            .any(|r| r.target_kind == "Secret" && r.target_name == clean)
                    {
                        identity.relationships.push(NativeRelationship {
                            rel_type: RelationshipType::CONSUMES,
                            target_kind: "Secret".to_string(),
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
    fn test_extract_secret_refs() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: pod\nspec:\n  containers:\n  - name: app\n    env:\n    - name: DB_PASS\n      valueFrom:\n        secretKeyRef:\n          name: db-credentials\n          key: password";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "pod".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        SecretRefExtractor.extract(&shards, &mut id);
        assert!(id.secret_refs.contains(&"db-credentials".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "Secret" && r.target_name == "db-credentials"));
    }
}
