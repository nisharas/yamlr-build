//! Image Tag & Pull Policy Alignment (Rule IMG-002).
//!
//! Why: In Kubernetes workloads, image pull policies and tag patterns must align:
//! 1. Floating `:latest` or untagged images: Without `imagePullPolicy: Always`, nodes cache
//!    the first pulled version forever. Subsequent pods will run stale code and diverge across nodes.
//! 2. Immutable digests: Using `@sha256:` pins the exact byte image. Setting `imagePullPolicy: Always`
//!    wastes network bandwidth and causes deploy timeouts under container registry rate-limits.
//!
//! This module heals missing or misaligned `imagePullPolicy` to ensure determinism and reliability.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_IMG_002: &str = "IMG-002";

/// Checks if an image identifier has no tag or uses the floating :latest tag.
pub fn is_floating_or_latest_tag(image_ref: &str) -> bool {
    let clean = image_ref.trim().trim_matches(|c| c == '\'' || c == '"');
    if clean.is_empty() {
        return false;
    }
    // Hash digest is never floating
    if clean.contains('@') {
        return false;
    }
    // Ends with :latest
    if clean.ends_with(":latest") {
        return true;
    }
    // Check if there is an explicit tag after the last colon (avoiding port in registry host)
    let parts: Vec<&str> = clean.rsplitn(2, ':').collect();
    if parts.len() == 1 {
        // No colon at all: e.g. "nginx" -> implicit latest
        return true;
    }
    // If the colon was part of registry port (e.g. localhost:5000/myimage)
    if parts[0].contains('/') {
        return true;
    }
    false
}

/// Aligns imagePullPolicy on a container node based on image tag semantics.
pub fn align_container_image_pull_policy(
    container: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let container_name = container
        .find_value("name")
        .unwrap_or_else(|| "unknown".to_string());

    let image_val = match container.find_value("image") {
        Some(v) => v,
        None => return,
    };

    let is_latest = is_floating_or_latest_tag(&image_val);
    let existing_policy = container.find_value("imagePullPolicy");

    if is_latest {
        // Floating/latest tags MUST use Always
        if existing_policy.as_deref() != Some("Always") {
            if let Some(policy_node) = container.find_node_mut("imagePullPolicy") {
                policy_node.value = Some("Always".to_string());
                for s in &mut policy_node.shards {
                    s.value = Some("Always".to_string());
                }
            } else {
                container.children.push(SemanticNode {
                    key: "imagePullPolicy".to_string(),
                    value: Some("Always".to_string()),
                    indent: container.indent + 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                });
            }
            let msg = format!(
                "Remediation [{}]: Enforced 'imagePullPolicy: Always' for floating/latest image '{}' in container '{}'.",
                RULE_IMG_002, image_val, container_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }
}

/// Primary Entrypoint: Aligns imagePullPolicy across all workload containers.
pub fn heal_image_pull_policy(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    for c_node in manifest.root.find_nodes_by_key_recursive_mut("containers") {
        for container in &mut c_node.children {
            align_container_image_pull_policy(container, telemetry, &mut changes);
        }
    }

    for c_node in manifest.root.find_nodes_by_key_recursive_mut("initContainers") {
        for container in &mut c_node.children {
            align_container_image_pull_policy(container, telemetry, &mut changes);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_floating_or_latest_tag() {
        assert!(is_floating_or_latest_tag("nginx"));
        assert!(is_floating_or_latest_tag("nginx:latest"));
        assert!(is_floating_or_latest_tag("docker.io/library/alpine:latest"));
        assert!(is_floating_or_latest_tag("localhost:5000/app"));

        assert!(!is_floating_or_latest_tag("nginx:1.25.0"));
        assert!(!is_floating_or_latest_tag("redis:7.0-alpine"));
        assert!(!is_floating_or_latest_tag("app@sha256:abcdef1234567890"));
    }
}
