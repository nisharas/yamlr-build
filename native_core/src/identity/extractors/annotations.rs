//! Annotation Extractor
//!
//! Why: Extracts metadata.annotations key-value pairs for cross-resource inspection,
//! policy auditing, and ingress/cert-manager controller bindings.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeShard};

pub struct AnnotationExtractor;

impl NativeMetadataExtractor for AnnotationExtractor {
    fn name(&self) -> &'static str {
        "AnnotationExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let paths = iter_shard_paths(shards);
        for (path, s) in paths {
            if let Some(ann_key) = path.strip_prefix("metadata.annotations.") {
                if !ann_key.is_empty() {
                    if let Some(val) = &s.value {
                        let clean_val = val.trim_matches(|c| c == '"' || c == '\'');
                        identity
                            .annotations
                            .insert(ann_key.to_string(), clean_val.to_string());
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
    fn test_extract_annotations() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n  annotations:\n    app.kubernetes.io/managed-by: Helm\n    prometheus.io/scrape: \"true\"";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "test".to_string(),
            ..Default::default()
        };
        AnnotationExtractor.extract(&shards, &mut id);
        assert_eq!(
            id.annotations.get("app.kubernetes.io/managed-by"),
            Some(&"Helm".to_string())
        );
        assert_eq!(
            id.annotations.get("prometheus.io/scrape"),
            Some(&"true".to_string())
        );
    }
}
