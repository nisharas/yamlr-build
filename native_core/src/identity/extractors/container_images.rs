//! Container Image Extractor
//!
//! Why: Extracts container image references across containers, initContainers,
//! and ephemeralContainers to audit mutable tags, registries, and CVE risk.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeShard};

pub struct ContainerImageExtractor;

impl NativeMetadataExtractor for ContainerImageExtractor {
    fn name(&self) -> &'static str {
        "ContainerImageExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let paths = iter_shard_paths(shards);
        for (_path, s) in paths {
            if s.key == "image" {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    if !clean.is_empty() && !identity.container_images.contains(&clean) {
                        identity.container_images.push(clean);
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
    fn test_extract_container_images() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: pod\nspec:\n  initContainers:\n  - name: init\n    image: busybox:1.36\n  containers:\n  - name: web\n    image: nginx:1.25-alpine";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "pod".to_string(),
            ..Default::default()
        };
        ContainerImageExtractor.extract(&shards, &mut id);
        assert_eq!(id.container_images.len(), 2);
        assert!(id.container_images.contains(&"busybox:1.36".to_string()));
        assert!(id
            .container_images
            .contains(&"nginx:1.25-alpine".to_string()));
    }
}
