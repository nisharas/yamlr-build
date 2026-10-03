//! Container Port Extractor
//!
//! Why: Extracts container ports declared in workloads to validate against
//! Service targetPort definitions and prevent traffic black-holing.

use super::NativeMetadataExtractor;
use crate::models::{NativeIdentity, NativeShard};

pub struct ContainerPortExtractor;

impl NativeMetadataExtractor for ContainerPortExtractor {
    fn name(&self) -> &'static str {
        "ContainerPortExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let mut current_name: Option<String> = None;
        for s in shards {
            if s.key.eq_ignore_ascii_case("name") && s.original_indent >= 4 {
                if let Some(val) = &s.value {
                    current_name = Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
                }
            } else if s.key.eq_ignore_ascii_case("containerPort") {
                if let Some(val) = &s.value {
                    if let Ok(port) = val.trim_matches(|c| c == '"' || c == '\'').parse::<i32>() {
                        if !identity.ports.contains(&port) {
                            identity.ports.push(port);
                        }
                        identity
                            .container_port_defs
                            .push((current_name.take(), port));
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
    fn test_extract_container_ports() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: pod\nspec:\n  containers:\n  - name: web\n    ports:\n    - containerPort: 8080\n    - containerPort: 9090";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Pod".to_string(),
            name: "pod".to_string(),
            ..Default::default()
        };
        ContainerPortExtractor.extract(&shards, &mut id);
        assert!(id.ports.contains(&8080));
        assert!(id.ports.contains(&9090));
    }
}
