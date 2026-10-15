//! CoreDNS ExternalName FQDN Healer & HostPort Anti-Affinity Synthesizer (Rules NET-009, NET-010).
//!
//! Why:
//! 1. NET-009: In Kubernetes, `type: ExternalName` without a trailing dot (e.g. `externalName: api.stripe.com`)
//!    causes CoreDNS query amplification. Linux `/etc/resolv.conf` searches cluster suffixes
//!    (`api.stripe.com.default.svc.cluster.local`, etc.), triggering 4-5 redundant DNS lookups,
//!    increasing latency, and overwhelming CoreDNS pods. Adding a trailing dot (`api.stripe.com.`) makes it absolute.
//! 2. NET-010: Deployments with `hostPort` and `replicas > 1` without pod anti-affinity will fail to schedule
//!    when two replicas land on the same node (`Address already in use`). Synthesizing `podAntiAffinity`
//!    on `kubernetes.io/hostname` guarantees pods land on distinct nodes.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_NET_009: &str = "NET-009";
pub const RULE_NET_010: &str = "NET-010";
pub const RULE_NET_012: &str = "NET-012";

/// Heals ExternalName services by ensuring a trailing dot on external FQDNs.
pub fn heal_external_name_dns(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return changes;
    }

    let svc_type = manifest
        .root
        .find_node("spec")
        .and_then(|s| s.find_value("type"))
        .unwrap_or_default();

    if svc_type != "ExternalName" {
        return changes;
    }

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(ext_node) = spec.find_node_mut("externalName") {
            if let Some(val) = &ext_node.value {
                let trimmed = val.trim().trim_matches(|c| c == '\'' || c == '"');
                // If it contains a dot (is a domain) but does not end with a dot, and is not an IP address
                if trimmed.contains('.') && !trimmed.ends_with('.') && trimmed.parse::<std::net::IpAddr>().is_err() {
                    let absolute_fqdn = format!("{}.", trimmed);
                    let msg = format!(
                        "Remediation [{}]: Appended trailing dot to ExternalName '{}' -> '{}' to prevent CoreDNS search path amplification loops.",
                        RULE_NET_009, trimmed, absolute_fqdn
                    );
                    ext_node.value = Some(absolute_fqdn.clone());
                    for s in &mut ext_node.shards {
                        s.value = Some(absolute_fqdn.clone());
                    }
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    changes
}

/// Synthesizes podAntiAffinity when a multi-replica workload specifies hostPort.
pub fn heal_hostport_anti_affinity(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Deployment" && kind != "StatefulSet" {
        return changes;
    }

    let replicas = manifest
        .root
        .find_node("spec")
        .and_then(|s| s.find_value("replicas"))
        .and_then(|v| v.trim_matches('"').parse::<u32>().ok())
        .unwrap_or(1);

    if replicas <= 1 {
        return changes;
    }

    // Check if any container declares hostPort
    let mut has_hostport = false;
    for c_node in manifest.root.find_nodes_by_key_recursive("containers") {
        for c in &c_node.children {
            if let Some(ports) = c.find_node("ports") {
                for p in &ports.children {
                    if p.find_node("hostPort").is_some() {
                        has_hostport = true;
                        break;
                    }
                }
            }
        }
    }

    if !has_hostport {
        return changes;
    }

    let app_label = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_node("labels"))
        .and_then(|l| l.find_value("app"))
        .unwrap_or_else(|| "app".to_string());

    // Find pod spec
    for pod_spec in manifest.root.find_pod_specs_mut() {
        if pod_spec.find_node("affinity").is_none() {

            let p_indent = pod_spec.indent;
            let affinity_node = SemanticNode {
                key: "affinity".to_string(),
                value: None,
                indent: p_indent + 2,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "podAntiAffinity".to_string(),
                    value: None,
                    indent: p_indent + 4,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "requiredDuringSchedulingIgnoredDuringExecution".to_string(),
                        value: None,
                        indent: p_indent + 6,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "-".to_string(),
                            value: None,
                            indent: p_indent + 8,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![
                                SemanticNode {
                                    key: "topologyKey".to_string(),
                                    value: Some("kubernetes.io/hostname".to_string()),
                                    indent: p_indent + 10,
                                    is_empty_flow: false,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                },
                                SemanticNode {
                                    key: "labelSelector".to_string(),
                                    value: None,
                                    indent: p_indent + 10,
                                    is_empty_flow: false,
                                    shards: Vec::new(),
                                    children: vec![SemanticNode {
                                        key: "matchLabels".to_string(),
                                        value: None,
                                        indent: p_indent + 12,
                                        is_empty_flow: false,
                                        shards: Vec::new(),
                                        children: vec![SemanticNode {
                                            key: "app".to_string(),
                                            value: Some(app_label.clone()),
                                            indent: p_indent + 14,
                                            is_empty_flow: false,
                                            children: Vec::new(),
                                            shards: Vec::new(),
                                        }],
                                    }],
                                },
                            ],
                        }],
                    }],
                }],
            };

            pod_spec.children.push(affinity_node);
            let msg = format!(
                "Remediation [{}]: Synthesized 'podAntiAffinity' on kubernetes.io/hostname to prevent hostPort scheduling port collisions on multi-replica workload.",
                RULE_NET_010
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

/// Rule NET-012 (Trap 42): Normalizes headless Service `clusterIP: None` casing and unquotes string literals.
///
/// Why: StatefulSets and stateful clusters (Kafka, ZooKeeper, Redis, PostgreSQL) require headless Services
/// with `clusterIP: None` for direct Pod DNS record resolution. Developers commonly write `clusterIP: "None"`,
/// `clusterIP: none`, or `clusterIP: "none"`. Kubernetes `kube-apiserver` rejects lowercase or quoted variants
/// (`may not be set to 'none'`). This healer normalizes any case-insensitive "none" variant to the canonical `None`.
pub fn heal_headless_service_cluster_ip(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return changes;
    }

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(cluster_ip_node) = spec.find_node_mut("clusterIP") {
            if let Some(val) = &cluster_ip_node.value {
                let trimmed = val.trim();
                let clean = trimmed.trim_matches(|c| c == '\'' || c == '"');
                if clean.eq_ignore_ascii_case("none") && val != "None" {
                    let old_val = val.clone();
                    let canonical = "None".to_string();
                    cluster_ip_node.value = Some(canonical.clone());
                    for s in &mut cluster_ip_node.shards {
                        s.value = Some(canonical.clone());
                    }

                    let svc_name = manifest.root.find_node("metadata")
                        .and_then(|m| m.find_value("name"))
                        .unwrap_or_else(|| "unnamed".to_string());

                    let msg = format!(
                        "Remediation [{}]: Normalized headless Service '{}' clusterIP '{}' -> 'None'.",
                        RULE_NET_012, svc_name, old_val
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    changes
}

pub const RULE_NET_013: &str = "NET-013";

/// Rule NET-013 (Trap 49): Validates, clamps, and unquotes `spec.sessionAffinityConfig.clientIP.timeoutSeconds`.
///
/// Why: In Kubernetes `Service`, when `sessionAffinity: ClientIP` is configured, `timeoutSeconds` specifies
/// client stickiness duration. The Kubernetes OpenAPI schema and kube-apiserver enforce:
/// 1. Type: strict unquoted integer scalar (quoted `"10800"` causes admission rejection).
/// 2. Range: strictly between 1 and 86400 (24 hours). If set > 86400 (e.g. 100000), kube-apiserver
///    immediately rejects: `spec.sessionAffinityConfig.clientIP.timeoutSeconds: Invalid value: 100000: must be between 1 and 86400`.
/// 3. Zero-assumption: Any value exceeding 86400 is safely clamped to 86400, preserving maximum allowable stickiness.
pub fn heal_session_affinity_timeout(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return changes;
    }

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(sac_node) = spec.find_node_mut("sessionAffinityConfig") {
            if let Some(client_ip_node) = sac_node.find_node_mut("clientIP") {
                if let Some(timeout_node) = client_ip_node.find_node_mut("timeoutSeconds") {
                    if let Some(val) = &timeout_node.value {
                        let trimmed = val.trim();
                        let clean = trimmed.trim_matches(|c| c == '\'' || c == '"');
                        if let Ok(mut num) = clean.parse::<i64>() {
                            if num <= 0 {
                                num = 1;
                            } else if num > 86400 {
                                num = 86400;
                            }

                            let canonical = num.to_string();
                            if *val != canonical {
                                let old_val = val.clone();
                                timeout_node.value = Some(canonical.clone());
                                for s in &mut timeout_node.shards {
                                    s.value = Some(canonical.clone());
                                }

                                let svc_name = manifest.root.find_node("metadata")
                                    .and_then(|m| m.find_value("name"))
                                    .unwrap_or_else(|| "unnamed".to_string());

                                let msg = format!(
                                    "Remediation [{}]: Clamped/normalized sessionAffinityConfig timeoutSeconds '{}' -> '{}' (max 86400s) on Service '{}'.",
                                    RULE_NET_013, old_val, canonical, svc_name
                                );
                                native_record_healing_impact(telemetry, &msg);
                                changes.push(msg);
                            }
                        }
                    }
                }
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_external_name_dns_healer() {
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
                        value: Some("Service".to_string()),
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
                                key: "type".to_string(),
                                value: Some("ExternalName".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                            SemanticNode {
                                key: "externalName".to_string(),
                                value: Some("api.stripe.com".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                        ],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_external_name_dns(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let ext_val = manifest.root.find_node("spec").unwrap().find_value("externalName").unwrap();
        assert_eq!(ext_val, "api.stripe.com.");
    }

    #[test]
    fn test_heal_headless_service_cluster_ip() {
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
                        value: Some("Service".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "metadata".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "name".to_string(),
                                value: Some("kafka-headless".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                        ],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "clusterIP".to_string(),
                                value: Some("\"none\"".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                        ],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_headless_service_cluster_ip(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let cip = manifest.root.find_node("spec").unwrap().find_value("clusterIP").unwrap();
        assert_eq!(cip, "None");
    }

    #[test]
    fn test_heal_session_affinity_timeout_clamping() {
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
                        value: Some("Service".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    },
                    SemanticNode {
                        key: "metadata".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "name".to_string(),
                                value: Some("sticky-svc".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                        ],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![
                            SemanticNode {
                                key: "sessionAffinity".to_string(),
                                value: Some("ClientIP".to_string()),
                                indent: 2,
                                is_empty_flow: false,
                                children: Vec::new(),
                                shards: Vec::new(),
                            },
                            SemanticNode {
                                key: "sessionAffinityConfig".to_string(),
                                value: None,
                                indent: 2,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: vec![
                                    SemanticNode {
                                        key: "clientIP".to_string(),
                                        value: None,
                                        indent: 4,
                                        is_empty_flow: false,
                                        shards: Vec::new(),
                                        children: vec![
                                            SemanticNode {
                                                key: "timeoutSeconds".to_string(),
                                                value: Some("\"100000\"".to_string()), // Quoted and > 86400
                                                indent: 6,
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
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_session_affinity_timeout(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("[NET-013]"));

        let spec = manifest.root.find_node("spec").unwrap();
        let sac = spec.find_node("sessionAffinityConfig").unwrap();
        let cip = sac.find_node("clientIP").unwrap();
        assert_eq!(cip.find_value("timeoutSeconds"), Some("86400".to_string()));
    }
}

