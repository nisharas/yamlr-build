//! Container Port Extractor
//!
//! Why: Extracts container ports declared in workloads to validate against
//! Service targetPort definitions and prevent traffic black-holing.
//! Handles arbitrary key ordering within port list items and scoped blocks.

use super::NativeMetadataExtractor;
use crate::models::{NativeIdentity, NativeShard};

pub struct ContainerPortExtractor;

impl NativeMetadataExtractor for ContainerPortExtractor {
    fn name(&self) -> &'static str {
        "ContainerPortExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        let mut in_ports = false;
        let mut ports_indent = 0;
        let mut current_name: Option<String> = None;
        let mut current_port: Option<i32> = None;

        let flush = |name: &mut Option<String>, port: &mut Option<i32>, id: &mut NativeIdentity| {
            if let Some(p) = port.take() {
                if !id.ports.contains(&p) {
                    id.ports.push(p);
                }
                id.container_port_defs.push((name.take(), p));
            } else {
                *name = None;
            }
        };

        for s in shards {
            if s.key.eq_ignore_ascii_case("ports") && s.value.is_none() {
                flush(&mut current_name, &mut current_port, identity);
                in_ports = true;
                ports_indent = s.indent;
                continue;
            }

            if in_ports {
                if s.indent <= ports_indent && !s.is_list_item {
                    flush(&mut current_name, &mut current_port, identity);
                    in_ports = false;
                    continue;
                }

                if s.is_list_item {
                    flush(&mut current_name, &mut current_port, identity);
                }

                if s.key.eq_ignore_ascii_case("name") {
                    if let Some(val) = &s.value {
                        current_name = Some(val.trim_matches(|c| c == '"' || c == '\'').to_string());
                    }
                } else if s.key.eq_ignore_ascii_case("containerPort") {
                    if let Some(val) = &s.value {
                        if let Ok(port) = val.trim_matches(|c| c == '"' || c == '\'').parse::<i32>() {
                            current_port = Some(port);
                        }
                    }
                }
            }
        }
        flush(&mut current_name, &mut current_port, identity);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_container_ports_arbitrary_order() {
        let raw = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-dep
spec:
  template:
    spec:
      containers:
      - name: controller
        ports:
        - containerPort: 8090
          name: policy-grpc
        - name: policy-https
          containerPort: 8443
"#;
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Deployment".to_string(),
            name: "test-dep".to_string(),
            ..Default::default()
        };
        ContainerPortExtractor.extract(&shards, &mut id);
        assert_eq!(id.ports, vec![8090, 8443]);
        assert_eq!(
            id.container_port_defs,
            vec![
                (Some("policy-grpc".to_string()), 8090),
                (Some("policy-https".to_string()), 8443)
            ]
        );
    }
}
