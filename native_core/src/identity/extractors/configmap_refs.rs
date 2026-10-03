//! ConfigMap Reference Extractor
//!
//! Why: Extracts ConfigMap dependencies from envFrom, valueFrom.configMapKeyRef,
//! and volume projections to detect missing or broken ConfigMap resources.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct ConfigMapKeyRefExtractor;

impl NativeMetadataExtractor for ConfigMapKeyRefExtractor {
    fn name(&self) -> &'static str {
        "ConfigMapKeyRefExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let paths = iter_shard_paths(shards);
        for (path, s) in paths {
            let is_cm_ref = (path.contains("configMapKeyRef") && s.key == "name")
                || (path.contains("configMapRef") && s.key == "name")
                || (path.contains("volumes") && path.contains("configMap") && s.key == "name")
                || (s.key.eq_ignore_ascii_case("configMapName")
                    || s.key.eq_ignore_ascii_case("configMapRef"));

            if is_cm_ref {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    if !clean.is_empty() && !identity.config_refs.contains(&clean) {
                        identity.config_refs.push(clean.clone());
                    }
                    if !clean.is_empty()
                        && !identity
                            .relationships
                            .iter()
                            .any(|r| r.target_kind == "ConfigMap" && r.target_name == clean)
                    {
                        identity.relationships.push(NativeRelationship {
                            rel_type: RelationshipType::CONSUMES,
                            target_kind: "ConfigMap".to_string(),
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
    fn test_extract_configmap_refs() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: pod\nspec:\n  containers:\n  - name: app\n    env:\n    - name: CFG\n      valueFrom:\n        configMapKeyRef:\n          name: app-cfg\n          key: log_level";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "pod".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        ConfigMapKeyRefExtractor.extract(&shards, &mut id);
        assert!(id.config_refs.contains(&"app-cfg".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "ConfigMap" && r.target_name == "app-cfg"));
    }
}
