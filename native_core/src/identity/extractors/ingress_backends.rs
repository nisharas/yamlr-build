//! Ingress Backend Service Extractor
//!
//! Why: Extracts target Service references from Ingress HTTP backend rules to
//! detect dead ingress routes pointing to non-existent Services.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct IngressBackendExtractor;

impl NativeMetadataExtractor for IngressBackendExtractor {
    fn name(&self) -> &'static str {
        "IngressBackendExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "Ingress" {
            return;
        }

        let paths = iter_shard_paths(shards);
        for (path, s) in paths {
            let is_backend_service =
                (path.contains("backend") && path.contains("service") && s.key == "name")
                    || (path.contains("backend") && s.key == "serviceName");

            if is_backend_service {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    if !clean.is_empty() && !identity.service_refs.contains(&clean) {
                        identity.service_refs.push(clean.clone());
                    }
                    if !clean.is_empty()
                        && !identity
                            .relationships
                            .iter()
                            .any(|r| r.target_kind == "Service" && r.target_name == clean)
                    {
                        identity.relationships.push(NativeRelationship {
                            rel_type: RelationshipType::CONNECTS,
                            target_kind: "Service".to_string(),
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
    fn test_extract_ingress_backends() {
        let raw = "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: app-ingress\nspec:\n  rules:\n  - http:\n      paths:\n      - path: /api\n        backend:\n          service:\n            name: api-svc\n            port:\n              number: 80";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Ingress".to_string(),
            name: "app-ingress".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };
        IngressBackendExtractor.extract(&shards, &mut id);
        assert!(id.service_refs.contains(&"api-svc".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.rel_type == RelationshipType::CONNECTS && r.target_name == "api-svc"));
    }
}
