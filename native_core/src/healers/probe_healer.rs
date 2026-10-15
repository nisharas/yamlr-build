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

    let has_startup = container.find_node("startupProbe").is_some();

    // Liveness Probe
    if let Some(liveness) = container.find_node_mut("livenessProbe") {
        // Rule REL-014: Probe Startup CrashLoop Safeguard
        // If container has liveness probe with missing or 0 initialDelaySeconds and no startupProbe,
        // inject initialDelaySeconds: 10 to prevent early termination during slow initialization.
        let initial_delay_val = liveness
            .find_node("initialDelaySeconds")
            .and_then(|n| n.value.as_ref())
            .and_then(|v| v.trim_matches('"').parse::<i32>().ok())
            .unwrap_or(0);

        if !has_startup && initial_delay_val == 0 {
            if let Some(delay_node) = liveness.find_node_mut("initialDelaySeconds") {
                delay_node.value = Some("10".to_string());
                for s in &mut delay_node.shards {
                    s.value = Some("10".to_string());
                }
            } else {
                liveness.children.push(SemanticNode {
                    key: "initialDelaySeconds".to_string(),
                    value: Some("10".to_string()),
                    indent: liveness.indent + 2,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                });
            }
            let msg = format!(
                "Remediation [REL-014]: Injected safe 'initialDelaySeconds: 10' on livenessProbe for container '{}' to prevent early CrashLoopBackOff.",
                container_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    } else {
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

/// Primary Entrypoint for REL-014: Ensures existing livenessProbes have safe initialDelaySeconds.
/// Runs unconditionally without requiring opt-in annotation because it fixes an existing, broken configuration.
pub fn heal_probe_crashloop_safeguards(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    let opt_in = manifest
        .root
        .find_annotation("yamlr.io/probe-safeguards")
        .or_else(|| manifest.root.find_annotation("yamlr.dev/probe-safeguards"))
        .or_else(|| manifest.root.find_annotation("yamlr.io/probes"))
        .or_else(|| manifest.root.find_annotation("yamlr.dev/probes"))
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);

    for c_node in manifest.root.find_nodes_by_key_recursive_mut("containers") {
        for container in &mut c_node.children {
            let container_name = container
                .find_value("name")
                .unwrap_or_else(|| "unknown".to_string());
            let has_startup = container.find_node("startupProbe").is_some();

            // Trap 66 / Rule PRB-006: Deadlock prevention when timeoutSeconds >= periodSeconds
            let probe_names = ["livenessProbe", "readinessProbe", "startupProbe"];
            for p_name in &probe_names {
                if let Some(probe_node) = container.find_node_mut(p_name) {
                    let timeout = probe_node
                        .find_node("timeoutSeconds")
                        .and_then(|n| n.value.as_ref())
                        .and_then(|v| v.trim_matches(|c| c == '\'' || c == '"').parse::<i32>().ok())
                        .unwrap_or(1);
                    let period = probe_node
                        .find_node("periodSeconds")
                        .and_then(|n| n.value.as_ref())
                        .and_then(|v| v.trim_matches(|c| c == '\'' || c == '"').parse::<i32>().ok())
                        .unwrap_or(10);

                    if timeout >= period && timeout > 0 {
                        let new_period = timeout + 1;
                        if let Some(pn) = probe_node.find_node_mut("periodSeconds") {
                            pn.value = Some(new_period.to_string());
                            for s in &mut pn.shards {
                                s.value = Some(new_period.to_string());
                            }
                        } else {
                            probe_node.children.push(SemanticNode {
                                key: "periodSeconds".to_string(),
                                value: Some(new_period.to_string()),
                                indent: probe_node.indent + 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            });
                        }
                        let msg = format!(
                            "Remediation [PRB-006]: Fixed probe deadlock on {} for container '{}': clamped periodSeconds ({}s) to {}s (must be > timeoutSeconds {}s).",
                            p_name, container_name, period, new_period, timeout
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }

            if let Some(liveness) = container.find_node_mut("livenessProbe") {
                let initial_delay_val = liveness
                    .find_node("initialDelaySeconds")
                    .and_then(|n| n.value.as_ref())
                    .and_then(|v| v.trim_matches('"').parse::<i32>().ok());

                // 1. Definite error: negative initialDelaySeconds is illegal in K8s schema (< 0 -> 0)
                if let Some(neg_val) = initial_delay_val {
                    if neg_val < 0 {
                        if let Some(delay_node) = liveness.find_node_mut("initialDelaySeconds") {
                            delay_node.value = Some("0".to_string());
                            for s in &mut delay_node.shards {
                                s.value = Some("0".to_string());
                            }
                            let msg = format!(
                                "Remediation [REL-014]: Corrected invalid negative 'initialDelaySeconds: {}' -> '0' on livenessProbe for container '{}'.",
                                neg_val, container_name
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                            continue;
                        }
                    }
                }

                // 2. Policy safeguard: inject initialDelaySeconds: 10 if missing/0 and opted-in
                if opt_in && !has_startup && initial_delay_val.unwrap_or(0) == 0 {
                    if let Some(delay_node) = liveness.find_node_mut("initialDelaySeconds") {
                        delay_node.value = Some("10".to_string());
                        for s in &mut delay_node.shards {
                            s.value = Some("10".to_string());
                        }
                    } else {
                        liveness.children.push(SemanticNode {
                            key: "initialDelaySeconds".to_string(),
                            value: Some("10".to_string()),
                            indent: liveness.indent + 2,
                            is_empty_flow: false,
                            children: Vec::new(),
                            shards: Vec::new(),
                        });
                    }
                    let msg = format!(
                        "Remediation [REL-014]: Injected safe 'initialDelaySeconds: 10' on livenessProbe for container '{}' to prevent early CrashLoopBackOff.",
                        container_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    changes
}

/// Injects synthesized liveness and readiness probes into containers when completely missing (Opt-in via annotation).
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

    #[test]
    fn test_probe_timeout_deadlock_prevention() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".to_string(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "kind".to_string(),
                        value: Some("Deployment".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "template".to_string(),
                                value: None,
                                indent: 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![
                                    SemanticNode {
                                        key: "spec".to_string(),
                                        value: None,
                                        indent: 4,
                                        is_empty_flow: false,
                                        shards: Vec::new(),
                                        children: vec![
                                            SemanticNode {
                                                key: "containers".to_string(),
                                                value: None,
                                                indent: 6,
                                                is_empty_flow: false,
                                                shards: Vec::new(),
                                                children: vec![
                                                    SemanticNode {
                                                        key: "-".to_string(),
                                                        value: None,
                                                        indent: 8,
                                                        is_empty_flow: false,
                                                        shards: Vec::new(),
                                                        children: vec![
                                                            SemanticNode {
                                                                key: "name".to_string(),
                                                                value: Some("api".to_string()),
                                                                indent: 10,
                                                                is_empty_flow: false,
                                                                children: Vec::new(),
                                                                shards: Vec::new(),
                                                            },
                                                            SemanticNode {
                                                                key: "livenessProbe".to_string(),
                                                                value: None,
                                                                indent: 10,
                                                                is_empty_flow: false,
                                                                shards: Vec::new(),
                                                                children: vec![
                                                                    SemanticNode {
                                                                        key: "timeoutSeconds".to_string(),
                                                                        value: Some("10".to_string()),
                                                                        indent: 12,
                                                                        is_empty_flow: false,
                                                                        children: Vec::new(),
                                                                        shards: Vec::new(),
                                                                    },
                                                                    SemanticNode {
                                                                        key: "periodSeconds".to_string(),
                                                                        value: Some("5".to_string()), // timeout > period!
                                                                        indent: 12,
                                                                        is_empty_flow: false,
                                                                        children: Vec::new(),
                                                                        shards: Vec::new(),
                                                                    },
                                                                ],
                                                            },
                                                        ],
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_probe_crashloop_safeguards(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("PRB-006"));

        let containers = manifest.root.find_nodes_by_key_recursive("containers");
        let lp = containers[0].children[0].find_node("livenessProbe").unwrap();
        assert_eq!(lp.find_value("periodSeconds"), Some("11".to_string()));
    }
}
