//! Service Selector Extractor
//!
//! Why: Extracts selector labels from Services to match against workload labels,
//! detecting unrouted services and labeling typos.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct ServiceSelectorExtractor;

impl NativeMetadataExtractor for ServiceSelectorExtractor {
    fn name(&self) -> &'static str {
        "ServiceSelectorExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "Service" {
            return;
        }

        let paths = iter_shard_paths(shards);
        for (path, s) in paths {
            if path.starts_with("spec.selector.") && !s.key.is_empty() {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    identity.selector.insert(s.key.clone(), clean);
                }
            }
        }

        if !identity.selector.is_empty() {
            let target_pod_desc = format!("{}-backend", identity.name);
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
    fn test_extract_service_selectors() {
        let raw = "apiVersion: v1\nkind: Service\nmetadata:\n  name: web-svc\nspec:\n  selector:\n    app: web\n    env: prod";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Service".to_string(),
            name: "web-svc".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        ServiceSelectorExtractor.extract(&shards, &mut id);
        assert_eq!(id.selector.get("app"), Some(&"web".to_string()));
        assert_eq!(id.selector.get("env"), Some(&"prod".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.rel_type == RelationshipType::SELECTS));
    }
}
