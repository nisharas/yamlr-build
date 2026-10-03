//! VerticalPodAutoscaler Target Reference Extractor
//!
//! Why: Extracts scaleTargetRef from VPA manifests so the discovery graph builder
//! can construct topology edges and detect cross-resource autoscaler contention
//! between HPAs and VPAs targeting the same workloads.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct VpaTargetExtractor;

impl NativeMetadataExtractor for VpaTargetExtractor {
    fn name(&self) -> &'static str {
        "VpaTargetExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "VerticalPodAutoscaler" && identity.kind != "VPA" {
            return;
        }

        let paths = iter_shard_paths(shards);
        let mut target_name = None;
        let mut target_kind = "Deployment".to_string();

        for (path, s) in paths {
            if path.contains("targetRef") {
                if s.key == "name" {
                    if let Some(val) = &s.value {
                        target_name = Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
                    }
                } else if s.key == "kind" {
                    if let Some(val) = &s.value {
                        target_kind = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    }
                }
            }
        }

        if let Some(name) = target_name {
            if !name.is_empty() && !identity.service_refs.contains(&name) {
                identity.service_refs.push(name.clone());
            }

            if !identity
                .relationships
                .iter()
                .any(|r| r.target_name == name && r.target_kind == target_kind)
            {
                identity.relationships.push(NativeRelationship {
                    rel_type: RelationshipType::CONNECTS,
                    target_kind,
                    target_name: name,
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
    fn test_extract_vpa_target_ref() {
        let raw = "apiVersion: autoscaling.k8s.io/v1\nkind: VerticalPodAutoscaler\nmetadata:\n  name: api-vpa\nspec:\n  targetRef:\n    apiVersion: apps/v1\n    kind: Deployment\n    name: api-service";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "VerticalPodAutoscaler".to_string(),
            name: "api-vpa".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        VpaTargetExtractor.extract(&shards, &mut id);
        assert_eq!(id.service_refs, vec!["api-service".to_string()]);
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_name == "api-service" && r.target_kind == "Deployment"));
    }
}
