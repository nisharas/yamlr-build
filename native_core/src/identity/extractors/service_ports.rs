//! Service Port Extractor
//!
//! Why: Extracts published ports and targetPorts from Service specs to match against
//! workload container ports and prevent orphaned listeners.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeShard};

pub struct ServicePortExtractor;

impl NativeMetadataExtractor for ServicePortExtractor {
    fn name(&self) -> &'static str {
        "ServicePortExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "Service" {
            return;
        }

        let paths = iter_shard_paths(shards);
        for (_path, s) in paths {
            let is_port_field = s.key.eq_ignore_ascii_case("port")
                || s.key.eq_ignore_ascii_case("targetPort")
                || s.key.eq_ignore_ascii_case("nodePort");

            if is_port_field {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'');
                    if let Ok(port_num) = clean.parse::<i32>() {
                        if !identity.ports.contains(&port_num) {
                            identity.ports.push(port_num);
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
    fn test_extract_service_ports() {
        let raw = "apiVersion: v1\nkind: Service\nmetadata:\n  name: web-svc\nspec:\n  ports:\n  - port: 80\n    targetPort: 8080\n    nodePort: 30080";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Service".to_string(),
            name: "web-svc".to_string(),
            ..Default::default()
        };
        ServicePortExtractor.extract(&shards, &mut id);
        assert!(id.ports.contains(&80));
        assert!(id.ports.contains(&8080));
        assert!(id.ports.contains(&30080));
    }
}
