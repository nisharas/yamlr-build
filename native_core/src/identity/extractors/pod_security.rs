//! Pod Security Context Extractor
//!
//! Why: Extracts pod and container-level securityContext parameters (runAsNonRoot,
//! runAsUser, fsGroup, privileged) for compliance and privilege-escalation auditing.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeShard};

pub struct PodSecurityContextExtractor;

impl NativeMetadataExtractor for PodSecurityContextExtractor {
    fn name(&self) -> &'static str {
        "PodSecurityContextExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let paths = iter_shard_paths(shards);
        let security_keys = [
            "runAsUser",
            "runAsNonRoot",
            "fsGroup",
            "readOnlyRootFilesystem",
            "privileged",
            "allowPrivilegeEscalation",
        ];

        for (path, s) in paths {
            if path.contains("securityContext") {
                for &target_key in &security_keys {
                    if s.key.eq_ignore_ascii_case(target_key) {
                        if let Some(val) = &s.value {
                            let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                            identity
                                .security_context
                                .insert(target_key.to_string(), clean);
                        }
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
    fn test_extract_pod_security_context() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: pod\nspec:\n  securityContext:\n    runAsNonRoot: true\n    fsGroup: 2000\n  containers:\n  - name: web\n    securityContext:\n      readOnlyRootFilesystem: true";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "pod".to_string(),
            ..Default::default()
        };
        PodSecurityContextExtractor.extract(&shards, &mut id);
        assert_eq!(
            id.security_context.get("runAsNonRoot"),
            Some(&"true".to_string())
        );
        assert_eq!(
            id.security_context.get("fsGroup"),
            Some(&"2000".to_string())
        );
        assert_eq!(
            id.security_context.get("readOnlyRootFilesystem"),
            Some(&"true".to_string())
        );
    }
}
