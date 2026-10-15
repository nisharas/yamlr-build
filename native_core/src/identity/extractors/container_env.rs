//! Container Environment Variable Extractor
//!
//! Why: Extracts literal container environment variables for secret leaks,
//! config drift detection, and forensic runtime analysis.
//! Handles arbitrary key ordering within env list items (e.g. value before name).

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
        let mut current_name: Option<String> = None;
        let mut current_value: Option<String> = None;

        let flush = |name: &mut Option<String>, val: &mut Option<String>, id: &mut NativeIdentity| {
            if let Some(n) = name.take() {
                if !n.is_empty() {
                    let v = val.take().unwrap_or_default();
                    id.container_envs.insert(n, v);
                }
            }
            *val = None;
        };

        for s in shards {
            if s.key.eq_ignore_ascii_case("env") && s.value.is_none() {
                flush(&mut current_name, &mut current_value, identity);
                in_env = true;
                env_indent = s.indent;
                continue;
            }

            if in_env {
                if s.indent <= env_indent && !s.is_list_item && !s.key.is_empty() {
                    flush(&mut current_name, &mut current_value, identity);
                    in_env = false;
                    continue;
                }

                if s.is_list_item {
                    flush(&mut current_name, &mut current_value, identity);
                }

                if s.key.eq_ignore_ascii_case("name") {
                    if let Some(v) = &s.value {
                        current_name = Some(v.trim_matches(|c| c == '"' || c == '\'').to_string());
                    }
                } else if s.key.eq_ignore_ascii_case("value") {
                    let v = s
                        .value
                        .as_deref()
                        .unwrap_or("")
                        .trim_matches(|c| c == '"' || c == '\'');
                    current_value = Some(v.to_string());
                }
            }
        }
        flush(&mut current_name, &mut current_value, identity);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_container_env_arbitrary_key_ordering() {
        let raw = r#"
apiVersion: v1
kind: Pod
metadata:
  name: pod
spec:
  containers:
  - name: web
    env:
    - name: ENV_MODE
      value: production
    - value: "true"
      name: DEBUG_ENABLED
"#;
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
        assert_eq!(
            id.container_envs.get("DEBUG_ENABLED"),
            Some(&"true".to_string())
        );
    }
}
