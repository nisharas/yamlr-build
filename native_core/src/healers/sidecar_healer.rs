//! Modern K8s 1.28+ Native Sidecar Modernizer (Feature 17).
//!
//! Why: In K8s < 1.28, sidecars placed in `spec.containers` caused severe race conditions
//! (app starts before proxy is ready, or batch jobs never terminate).
//! Kubernetes 1.28+ introduced native sidecars inside `initContainers` with `restartPolicy: Always`.
//! This module upgrades legacy sidecars into native sidecars.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const SIDECAR_RULE_ID: &str = "ARC-003";

pub static KNOWN_SIDECAR_NAMES: &[&str] = &[
    "istio-proxy",
    "envoy",
    "vault-agent",
    "fluentbit",
    "fluentd",
    "datadog-agent",
    "linkerd-proxy",
    "cloud-sql-proxy",
    "oauth2-proxy",
    "aws-iam-authenticator",
];

/// Helper: Identifies if a container name indicates a sidecar proxy/agent.
pub fn is_known_sidecar_name(name: &str) -> bool {
    let lower = name.to_lowercase();
    KNOWN_SIDECAR_NAMES.iter().any(|&s| lower.contains(s))
}

/// Primary entrypoint: Promotes legacy sidecars in `spec.containers` to native `initContainers`.
pub fn heal_legacy_sidecars(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    // Workload specs or Pod specs
    for spec in manifest.root.find_pod_specs_mut() {
        // Collect indices of sidecar containers in `containers`
        let mut sidecar_indices = Vec::new();
        if let Some(containers) = spec.find_node("containers") {
            for (idx, c) in containers.children.iter().enumerate() {
                let name = c.find_value("name").unwrap_or_default();
                if is_known_sidecar_name(&name) {
                    sidecar_indices.push((idx, name));
                }
            }
        }

        if sidecar_indices.is_empty() {
            // Also check if any existing initContainer is a sidecar missing restartPolicy: Always
            if let Some(init_containers) = spec.find_node_mut("initContainers") {
                for c in &mut init_containers.children {
                    let name = c.find_value("name").unwrap_or_default();
                    if is_known_sidecar_name(&name) {
                        if c.find_node("restartPolicy").is_none() {
                            let indent = c.indent + 2;
                            c.children.push(SemanticNode {
                                key: "restartPolicy".to_string(),
                                value: Some("Always".to_string()),
                                indent,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            });
                            let msg = format!(
                                "Remediation [{}]: Injected 'restartPolicy: Always' for native sidecar '{}'.",
                                SIDECAR_RULE_ID, name
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }
            continue;
        }

        // Extract the sidecar nodes
        let mut extracted_sidecars = Vec::new();
        let indent_base;
        if let Some(containers) = spec.find_node_mut("containers") {
            indent_base = containers.indent;
            // Remove from highest index to lowest
            for &(idx, _) in sidecar_indices.iter().rev() {
                let mut node = containers.children.remove(idx);
                // Ensure restartPolicy: Always is injected
                if node.find_node("restartPolicy").is_none() {
                    let item_indent = node.indent + 2;
                    node.children.push(SemanticNode {
                        key: "restartPolicy".to_string(),
                        value: Some("Always".to_string()),
                        indent: item_indent,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    });
                }
                extracted_sidecars.push(node);
            }
        } else {
            continue;
        }

        // Reverse to maintain original order
        extracted_sidecars.reverse();

        // Inject into `initContainers`
        if let Some(init_containers) = spec.find_node_mut("initContainers") {
            init_containers.children.extend(extracted_sidecars);
        } else {
            spec.children.push(SemanticNode {
                key: "initContainers".to_string(),
                value: None,
                indent: indent_base,
                is_empty_flow: false,
                children: extracted_sidecars,
                shards: Vec::new(),
            });
        }

        for (_, name) in sidecar_indices {
            let msg = format!(
                "Remediation [{}]: Upgraded legacy sidecar '{}' to K8s 1.28+ native sidecar in 'initContainers' (restartPolicy: Always).",
                SIDECAR_RULE_ID, name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_promote_legacy_sidecar() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "spec".to_string(),
                    value: None,
                    indent: 0,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "containers".to_string(),
                        value: None,
                        indent: 2,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "-".to_string(),
                                value: None,
                                indent: 4,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "name".to_string(),
                                    value: Some("app".to_string()),
                                    indent: 6,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                }],
                            },
                            SemanticNode {
                                key: "-".to_string(),
                                value: None,
                                indent: 4,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![SemanticNode {
                                    key: "name".to_string(),
                                    value: Some("istio-proxy".to_string()),
                                    indent: 6,
                                    is_empty_flow: false,
                                    children: vec![],
                                    shards: vec![],
                                }],
                            },
                        ],
                    }],
                }],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_legacy_sidecars(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);

        let spec = manifest.root.find_node("spec").unwrap();
        let containers = spec.find_node("containers").unwrap();
        assert_eq!(containers.children.len(), 1);
        assert_eq!(
            containers.children[0].find_value("name"),
            Some("app".to_string())
        );

        let init_containers = spec.find_node("initContainers").unwrap();
        assert_eq!(init_containers.children.len(), 1);
        let sidecar = &init_containers.children[0];
        assert_eq!(sidecar.find_value("name"), Some("istio-proxy".to_string()));
        assert_eq!(
            sidecar.find_value("restartPolicy"),
            Some("Always".to_string())
        );
    }
}
