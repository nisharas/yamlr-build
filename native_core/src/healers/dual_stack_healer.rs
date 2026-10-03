//! Dual-Stack IPv6 Service CIDR Clashes & Policy Healer (Rule NET-009).
//!
//! Why: In modern Kubernetes environments (AWS EKS with IPv6 prefix delegation,
//! GKE Dual-Stack clusters, AKS, or Cilium/Calico CNI), omitting `ipFamilyPolicy`
//! defaults Services to `SingleStack` (IPv4). When dual-stack cloud load balancers
//! (AWS NLB/ALB or GCP Cloud Load Balancing) attempt to route incoming IPv6 client
//! traffic, connections are blackholed because no IPv6 ClusterIPs or EndpointSlices
//! were allocated.
//!
//! Setting `ipFamilyPolicy: PreferDualStack` is universally safe: on dual-stack clusters,
//! Kubernetes automatically allocates dual-stack IPv4/IPv6 IPs; on legacy single-stack
//! clusters, Kubernetes smoothly degrades to IPv4 without admission rejections.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const DUAL_STACK_RULE_ID: &str = "NET-009";

/// Detects Services lacking ipFamilyPolicy on LoadBalancers and injects PreferDualStack.
pub fn heal_dual_stack_services(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return changes;
    }

    let svc_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-service".to_string());

    // Check if the service is a LoadBalancer or annotated for cloud load balancer routing
    let is_load_balancer = manifest
        .root
        .find_node("spec")
        .and_then(|s| s.find_value("type"))
        .map(|t| t.trim().trim_matches('"').trim_matches('\'') == "LoadBalancer")
        .unwrap_or(false);

    let has_cloud_lb_annotation = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_node("annotations"))
        .map(|ann| {
            ann.children.iter().any(|c| {
                let k = c.key.to_lowercase();
                k.starts_with("service.beta.kubernetes.io/aws-load-balancer-")
                    || k.starts_with("cloud.google.com/load-balancer-")
                    || k.starts_with("service.beta.kubernetes.io/azure-load-balancer-")
            })
        })
        .unwrap_or(false);

    let opt_in = manifest
        .root
        .find_annotation("yamlr.io/dual-stack")
        .map(|v| v.trim().trim_matches('"') == "true")
        .unwrap_or(false);

    // Apply if it's a LoadBalancer, cloud-annotated LB, or user opted in
    if !is_load_balancer && !has_cloud_lb_annotation && !opt_in {
        return changes;
    }

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        let has_policy = spec.find_node("ipFamilyPolicy").is_some();
        let indent = spec.indent + 2;

        if !has_policy {
            spec.children.push(SemanticNode {
                key: "ipFamilyPolicy".to_string(),
                value: Some("PreferDualStack".to_string()),
                children: Vec::new(),
                shards: Vec::new(),
                indent,
                is_empty_flow: false,
            });

            let msg = format!(
                "Remediation [{}]: Injected 'ipFamilyPolicy: PreferDualStack' on Service '{}' to prevent dual-stack IPv6 traffic blackholes.",
                DUAL_STACK_RULE_ID, svc_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }

        // When ipFamilies is explicitly set to ["IPv4"] but user opted in to dual-stack, append IPv6
        if opt_in {
            if let Some(ip_families) = spec.find_node_mut("ipFamilies") {
                let has_ipv4 = ip_families
                    .children
                    .iter()
                    .any(|c| c.value.as_deref() == Some("IPv4") || c.key == "IPv4");
                let has_ipv6 = ip_families
                    .children
                    .iter()
                    .any(|c| c.value.as_deref() == Some("IPv6") || c.key == "IPv6");
                if has_ipv4 && !has_ipv6 {
                    let fam_indent = ip_families.indent + 2;
                    ip_families.children.push(SemanticNode {
                        key: "-".to_string(),
                        value: Some("IPv6".to_string()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent: fam_indent,
                        is_empty_flow: false,
                    });
                    let msg = format!(
                        "Remediation [{}]: Appended 'IPv6' to 'spec.ipFamilies' on Service '{}' per dual-stack opt-in.",
                        DUAL_STACK_RULE_ID, svc_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::SemanticNode;

    #[test]
    fn test_inject_prefer_dual_stack_on_loadbalancer() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Service".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "name".into(),
                            value: Some("gateway-lb".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "type".into(),
                            value: Some("LoadBalancer".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                ],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            indent_step: 2,
            integrity_violations: vec![],
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_dual_stack_services(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(
            spec.find_value("ipFamilyPolicy"),
            Some("PreferDualStack".to_string())
        );
    }

    #[test]
    fn test_preserve_existing_dual_stack_policy() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Service".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "type".into(),
                                value: Some("LoadBalancer".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "ipFamilyPolicy".into(),
                                value: Some("RequireDualStack".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                        ],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                ],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            indent_step: 2,
            integrity_violations: vec![],
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_dual_stack_services(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 0);
        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(
            spec.find_value("ipFamilyPolicy"),
            Some("RequireDualStack".to_string())
        );
    }

    #[test]
    fn test_ignore_standard_cluster_ip_without_annotation() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Service".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "type".into(),
                            value: Some("ClusterIP".into()),
                            children: vec![],
                            shards: vec![],
                            indent: 2,
                            is_empty_flow: false,
                        }],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                ],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            indent_step: 2,
            integrity_violations: vec![],
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_dual_stack_services(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 0);
    }

    #[test]
    fn test_append_ipv6_to_ipfamilies_on_opt_in() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Service".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "name".into(),
                                value: Some("optin-svc".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "annotations".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "yamlr.io/dual-stack".into(),
                                    value: Some("\"true\"".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                }],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                        ],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "ipFamilyPolicy".into(),
                                value: Some("PreferDualStack".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "ipFamilies".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "-".into(),
                                    value: Some("IPv4".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 4,
                                    is_empty_flow: false,
                                }],
                                shards: vec![],
                                indent: 2,
                                is_empty_flow: false,
                            },
                        ],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                ],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            indent_step: 2,
            integrity_violations: vec![],
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_dual_stack_services(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        let ip_families = spec.find_node("ipFamilies").unwrap();
        assert_eq!(ip_families.children.len(), 2);
        assert_eq!(ip_families.children[1].value, Some("IPv6".to_string()));
    }
}
