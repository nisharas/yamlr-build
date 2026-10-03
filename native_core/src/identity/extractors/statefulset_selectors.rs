//! StatefulSet Selector Extractor
//!
//! Why: Extracts matchLabels for StatefulSets to verify persistent pod identity
//! and ensure headless Services align with StatefulSet member pods.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct StatefulSetSelectorExtractor;

impl NativeMetadataExtractor for StatefulSetSelectorExtractor {
    fn name(&self) -> &'static str {
        "StatefulSetSelectorExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "StatefulSet" {
            return;
        }

        let paths = iter_shard_paths(shards);
        for (path, s) in paths {
            if (path.contains("spec.selector.matchLabels") || path.contains("spec.selector"))
                && !s.key.is_empty()
            {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    identity.selector.insert(s.key.clone(), clean);
                }
            }
        }

        if !identity.selector.is_empty() {
            let target_pod_desc = format!("{}-pods", identity.name);
            if !identity
                .relationships
                .iter()
                .any(|r| r.target_name == target_pod_desc)
            {
                identity.relationships.push(NativeRelationship {
                    rel_type: RelationshipType::SELECTS,
                    target_kind: "Pod".to_string(),
                    target_name: target_pod_desc,
                    target_namespace: Some(identity.namespace.clone()),
                });
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_statefulset_selectors() {
        let raw = "apiVersion: apps/v1\nkind: StatefulSet\nmetadata:\n  name: kafka\nspec:\n  selector:\n    matchLabels:\n      app: kafka";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "StatefulSet".to_string(),
            name: "kafka".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        StatefulSetSelectorExtractor.extract(&shards, &mut id);
        assert_eq!(id.selector.get("app"), Some(&"kafka".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.rel_type == RelationshipType::SELECTS));
    }
}
