//! Probes Best Practice Auto-Healer (Feature 11 of 15).
//!
//! Why: Containers without `livenessProbe` and `readinessProbe` can experience silent deadlocks,
//! crash loops, and receive customer traffic before they are initialized, causing HTTP 502/504 errors.
//!
//! This module analyzes container ports to synthesize contextual, production-grade probes
//! (HTTP GET `/healthz` for web services, or TCP socket probes for background daemons).

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub static COMMON_HTTP_PORTS: &[i32] = &[80, 443, 8080, 8000, 3000, 5000, 9090];

/// Builds a default probe SemanticNode based on detected container port and protocol.
pub fn build_default_probe_node(
    probe_key: &str,
    port: i32,
    is_http: bool,
    indent: usize,
) -> SemanticNode {
    let mut probe_children = Vec::new();

    if is_http {
        let http_get = SemanticNode {
            key: "httpGet".to_string(),
            value: None,
            indent: indent + 2,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![
                SemanticNode {
                    key: "path".to_string(),
                    value: Some("/healthz".to_string()),
                    indent: indent + 4,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
                SemanticNode {
                    key: "port".to_string(),
                    value: Some(port.to_string()),
                    indent: indent + 4,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
            ],
        };
        probe_children.push(http_get);
    } else {
        let tcp_socket = SemanticNode {
            key: "tcpSocket".to_string(),
            value: None,
            indent: indent + 2,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "port".to_string(),
                value: Some(port.to_string()),
                indent: indent + 4,
                is_empty_flow: false,
                children: Vec::new(),
                shards: Vec::new(),
            }],
        };
        probe_children.push(tcp_socket);
    }

    probe_children.push(SemanticNode {
        key: "initialDelaySeconds".to_string(),
        value: Some("5".to_string()),
        indent: indent + 2,
        is_empty_flow: false,
        children: Vec::new(),
        shards: Vec::new(),
    });

    probe_children.push(SemanticNode {
        key: "periodSeconds".to_string(),
        value: Some("10".to_string()),
        indent: indent + 2,
        is_empty_flow: false,
        children: Vec::new(),
        shards: Vec::new(),
    });

    probe_children.push(SemanticNode {
        key: "timeoutSeconds".to_string(),
        value: Some("1".to_string()),
        indent: indent + 2,
        is_empty_flow: false,
        children: Vec::new(),
        shards: Vec::new(),
    });

    SemanticNode {
        key: probe_key.to_string(),
        value: None,
        indent,
        is_empty_flow: false,
        children: probe_children,
        shards: Vec::new(),
    }
}

/// Injects liveness and readiness probes into a container if missing.
pub fn ensure_container_probes(
    container: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let container_name = container
        .find_value("name")
        .unwrap_or_else(|| "unknown".to_string());

    // Skip sidecar / pause containers
    if container_name.contains("istio-proxy")
        || container_name.contains("vault-agent")
        || container_name.contains("pause")
    {
        return;
    }

    // Determine target port
    let mut detected_port = 8080;
    let mut is_http = true;

    if let Some(ports) = container.find_node("ports") {
        if let Some(first_port) = ports.children.first() {
            if let Some(p) = first_port
                .find_value("containerPort")
                .and_then(|v| v.parse::<i32>().ok())
            {
                detected_port = p;
                is_http = COMMON_HTTP_PORTS.contains(&p);
            }
        }
    }

    let c_indent = container.indent + 2;

    // Liveness Probe
    if container.find_node("livenessProbe").is_none() {
        let probe = build_default_probe_node("livenessProbe", detected_port, is_http, c_indent);
        container.children.push(probe);
        let msg = format!(
            "Remediation [REL-008]: Injected default livenessProbe (port {}) for container '{}'.",
            detected_port, container_name
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }

    // Readiness Probe
    if container.find_node("readinessProbe").is_none() {
        let probe = build_default_probe_node("readinessProbe", detected_port, is_http, c_indent);
        container.children.push(probe);
        let msg = format!(
            "Remediation [REL-008]: Injected default readinessProbe (port {}) for container '{}'.",
            detected_port, container_name
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }
}

/// Primary Entrypoint: Ensures all workload containers have health probes defined.
pub fn heal_probes(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    for c_node in manifest.root.find_nodes_by_key_recursive_mut("containers") {
        for container in &mut c_node.children {
            ensure_container_probes(container, telemetry, &mut changes);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ensure_container_probes() {
        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();

        let mut container = SemanticNode {
            key: "-".to_string(),
            value: None,
            indent: 4,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "name".to_string(),
                value: Some("web".to_string()),
                indent: 6,
                is_empty_flow: false,
                children: Vec::new(),
                shards: Vec::new(),
            }],
        };

        ensure_container_probes(&mut container, &mut telemetry, &mut changes);
        assert_eq!(changes.len(), 2);
        assert!(container.find_node("livenessProbe").is_some());
        assert!(container.find_node("readinessProbe").is_some());
    }
}
