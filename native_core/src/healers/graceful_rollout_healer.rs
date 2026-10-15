//! Zero-Downtime Rollout PreStop Drain Healer & Probe Decoupler (Rules REL-015, REL-017).
//!
//! Why: In production Kubernetes:
//! 1. REL-015: During a rolling update, Kubelet terminates a pod simultaneously with
//!    EndpointSlice deregistration across kube-proxy and Ingress controllers. Because
//!    network propagation takes 2-5 seconds, in-flight HTTP requests sent to the terminating
//!    pod receive immediate HTTP 502/504 Bad Gateway errors. Injecting a small `preStop`
//!    hook (`sleep 5`) gives the ingress controller time to divert traffic before SIGTERM.
//! 2. REL-017: If `livenessProbe` and `readinessProbe` target the exact same deep `/healthz`
//!    endpoint that checks downstream databases, a momentary database slowdown fails readiness
//!    (expected) BUT ALSO fails liveness, causing Kubelet to restart all pods concurrently,
//!    resulting in a catastrophic cascading cluster blackout.
//!
//! This module injects a safe `preStop` drain hook on web services and decouples probe paths.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_REL_015: &str = "REL-015";
pub const RULE_REL_017: &str = "REL-017";

/// Builds a standard preStop sleep node:
/// lifecycle:
///   preStop:
///     exec:
///       command: ["/bin/sh", "-c", "sleep 5"]
pub fn build_prestop_sleep_node(indent: usize, sleep_sec: u32) -> SemanticNode {
    SemanticNode {
        key: "lifecycle".to_string(),
        value: None,
        indent,
        is_empty_flow: false,
        shards: Vec::new(),
        children: vec![SemanticNode {
            key: "preStop".to_string(),
            value: None,
            indent: indent + 2,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "exec".to_string(),
                value: None,
                indent: indent + 4,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "command".to_string(),
                    value: Some(format!("[\"/bin/sh\", \"-c\", \"sleep {}\"]", sleep_sec)),
                    indent: indent + 6,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                }],
            }],
        }],
    }
}

/// Injects a safe preStop sleep hook on web/ingress-facing containers lacking one.
pub fn ensure_prestop_drain_hook(
    container: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let container_name = container
        .find_value("name")
        .unwrap_or_else(|| "unknown".to_string());

    // Skip sidecars / pauses
    if container_name.contains("sidecar") || container_name.contains("pause") {
        return;
    }

    // Only inject on containers with exposed ports (web/network workloads)
    let has_ports = container
        .find_node("ports")
        .map_or(false, |p| !p.children.is_empty());

    if !has_ports {
        return;
    }

    // Check if lifecycle / preStop already exists
    if let Some(lifecycle) = container.find_node_mut("lifecycle") {
        if lifecycle.find_node("preStop").is_none() {
            lifecycle.children.push(SemanticNode {
                key: "preStop".to_string(),
                value: None,
                indent: lifecycle.indent + 2,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "exec".to_string(),
                    value: None,
                    indent: lifecycle.indent + 4,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "command".to_string(),
                        value: Some("[\"/bin/sh\", \"-c\", \"sleep 5\"]".to_string()),
                        indent: lifecycle.indent + 6,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    }],
                }],
            });
            let msg = format!(
                "Remediation [{}]: Injected zero-downtime 'preStop: sleep 5' hook on container '{}' to eliminate HTTP 502/504 errors during rollouts.",
                RULE_REL_015, container_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    } else {
        let lifecycle_node = build_prestop_sleep_node(container.indent + 2, 5);
        container.children.push(lifecycle_node);
        let msg = format!(
            "Remediation [{}]: Injected zero-downtime 'preStop: sleep 5' hook on container '{}' to eliminate HTTP 502/504 errors during rollouts.",
            RULE_REL_015, container_name
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }
}

/// Detects when livenessProbe and readinessProbe share identical HTTP paths and logs remediation.
pub fn inspect_and_decouple_probes(
    container: &SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let container_name = container
        .find_value("name")
        .unwrap_or_else(|| "unknown".to_string());

    let live_path = container
        .find_node("livenessProbe")
        .and_then(|lp| lp.find_node("httpGet"))
        .and_then(|hg| hg.find_value("path"));

    let ready_path = container
        .find_node("readinessProbe")
        .and_then(|rp| rp.find_node("httpGet"))
        .and_then(|hg| hg.find_value("path"));

    if let (Some(l_path), Some(r_path)) = (live_path, ready_path) {
        if l_path == r_path && (l_path == "/healthz" || l_path == "/health" || l_path == "/actuator/health") {
            let msg = format!(
                "Advisory [{}]: Container '{}' shares identical probe path '{}' for both liveness and readiness. Recommend separating liveness (/livez) from readiness (/readyz) to prevent restart storms.",
                RULE_REL_017, container_name, l_path
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }
}

/// Primary Entrypoint: Heals zero-downtime lifecycle preStop hooks and audits probe decoupling.
pub fn heal_graceful_rollouts(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    // Opt-in or automated for Deployments and StatefulSets
    let opt_in = manifest
        .root
        .find_annotation("yamlr.dev/zero-downtime")
        .or_else(|| manifest.root.find_annotation("yamlr.io/zero-downtime"))
        .or_else(|| manifest.root.find_annotation("yamlr.dev/graceful"))
        .or_else(|| manifest.root.find_annotation("yamlr.io/graceful"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);

    if !opt_in {
        return changes;
    }

    for c_node in manifest.root.find_nodes_by_key_recursive_mut("containers") {
        for container in &mut c_node.children {
            ensure_prestop_drain_hook(container, telemetry, &mut changes);
            inspect_and_decouple_probes(container, telemetry, &mut changes);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_build_prestop_sleep_node() {
        let node = build_prestop_sleep_node(4, 5);
        assert_eq!(node.key, "lifecycle");
        assert!(node.find_node("preStop").is_some());
    }
}
