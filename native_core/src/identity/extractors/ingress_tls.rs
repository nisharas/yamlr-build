//! Ingress TLS Secret Extractor
//!
//! Why: Extracts TLS secretName references from Ingress specs to detect
//! missing TLS certificates and verify secret relationships.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};

pub struct IngressTlsExtractor;

impl NativeMetadataExtractor for IngressTlsExtractor {
    fn name(&self) -> &'static str {
        "IngressTlsExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "Ingress" {
            return;
        }

        let paths = iter_shard_paths(shards);
        for (_path, s) in paths {
            if s.key == "secretName" {
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
    fn test_extract_ingress_tls() {
        let raw = "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: secure-ingress\nspec:\n  tls:\n  - hosts:\n    - app.example.com\n    secretName: app-tls-cert";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Ingress".to_string(),
            name: "secure-ingress".to_string(),
            namespace: "prod".to_string(),
            ..Default::default()
        };
        IngressTlsExtractor.extract(&shards, &mut id);
        assert!(id.secret_refs.contains(&"app-tls-cert".to_string()));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "Secret" && r.target_name == "app-tls-cert"));
    }
}
