//! Container Environment Variable Extractor
//!
//! Why: Extracts literal container environment variables for secret leaks,
//! config drift detection, and forensic runtime analysis.

use super::NativeMetadataExtractor;
use crate::models::{NativeIdentity, NativeShard};

pub struct ContainerEnvExtractor;

impl NativeMetadataExtractor for ContainerEnvExtractor {
    fn name(&self) -> &'static str {
        "ContainerEnvExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let mut in_env = false;
        let mut env_indent = 0;
        let mut current_name = String::new();

        for s in shards {
            if s.key == "env" && s.value.is_none() {
                in_env = true;
                env_indent = s.indent;
                continue;
            }
            if in_env {
                if s.indent <= env_indent && !s.is_list_item && !s.key.is_empty() {
                    in_env = false;
                    current_name.clear();
                } else if s.key == "name" {
                    if let Some(val) = &s.value {
                        current_name = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    }
                } else if s.key == "value" && !current_name.is_empty() {
                    let val_str = s
                        .value
                        .as_deref()
                        .unwrap_or("")
                        .trim_matches(|c| c == '"' || c == '\'');
                    identity
                        .container_envs
                        .insert(current_name.clone(), val_str.to_string());
                    current_name.clear();
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_container_env() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: pod\nspec:\n  containers:\n  - name: web\n    env:\n    - name: ENV_MODE\n      value: production";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "pod".to_string(),
            ..Default::default()
        };
        ContainerEnvExtractor.extract(&shards, &mut id);
        assert_eq!(
            id.container_envs.get("ENV_MODE"),
            Some(&"production".to_string())
        );
    }
}
