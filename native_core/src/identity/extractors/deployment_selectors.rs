//! Deployment Selector Extractor
//!
//! Why: Extracts matchLabels for Deployments to verify pod-template alignment and
//! ensure Services correctly route to the Deployment's pods.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct DeploymentSelectorExtractor;

impl NativeMetadataExtractor for DeploymentSelectorExtractor {
    fn name(&self) -> &'static str {
        "DeploymentSelectorExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "Deployment" {
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
            if path == "spec.replicas" || s.key == "replicas" {
                if let Some(val) = &s.value {
                    let clean = val.trim().trim_matches(|c| c == '"' || c == '\'');
                    if let Ok(r) = clean.parse::<i32>() {
                        identity.replicas = Some(r);
                    }
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
    fn test_extract_deployment_selectors() {
        let raw = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web-deploy\nspec:\n  selector:\n    matchLabels:\n      app: web\n      tier: frontend";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Deployment".to_string(),
            name: "web-deploy".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        DeploymentSelectorExtractor.extract(&shards, &mut id);
        assert_eq!(id.selector.get("app"), Some(&"web".to_string()));
        assert_eq!(id.selector.get("tier"), Some(&"frontend".to_string()));
    }
}
