//! Gateway API TLSRoute and BackendTLSPolicy Modernizer & Healer (Rules MIG-005, SEC-015).
//!
//! Why: Gateway API v1.1 standardizes layer-4 TLS SNI routing (`TLSRoute`) and zero-trust
//! pod-to-pod backend encryption (`BackendTLSPolicy`). Manifests frequently contain unnormalized
//! hostnames, mismatched core API groups, or missing ConfigMap CA certificate references.

use crate::models::{NativeShard, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const GATEWAY_API_TLS_RULE_ID: &str = "MIG-005";
pub const BACKEND_TLS_POLICY_RULE_ID: &str = "SEC-015";

/// Heals Gateway API `TLSRoute` resources by sanitizing SNI hostnames to lowercase RFC 1123,
/// validating TLS passthrough/termination routing, and injecting required backend ports.
pub fn heal_tls_routes(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "TLSRoute" {
        return changes;
    }

    let route_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-route".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        // 1. Sanitize hostnames (SNI) to lowercase RFC 1123 without trailing dots or ports
        if let Some(hostnames_node) = spec.find_node_mut("hostnames") {
            for item in &mut hostnames_node.children {
                if let Some(val) = item.value.clone() {
                    let clean = val
                        .trim()
                        .trim_matches('"')
                        .trim_matches('\'')
                        .trim_end_matches('.');
                    let clean_no_port = clean.split(':').next().unwrap_or(clean);
                    let lower = clean_no_port.to_lowercase();
                    if lower != val.trim_matches('"').trim_matches('\'') {
                        let new_val = format!("\"{}\"", lower);
                        item.value = Some(new_val.clone());
                        for s in &mut item.shards {
                            s.value = Some(new_val.clone());
                        }
                        let msg = format!(
                            "Remediation [{}]: Sanitized TLSRoute '{}' hostname '{}' -> '{}'.",
                            GATEWAY_API_TLS_RULE_ID, route_name, val, lower
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }

        // 2. Validate backendRefs have explicit port defined
        if let Some(rules_node) = spec.find_node_mut("rules") {
            for rule in &mut rules_node.children {
                if let Some(backend_refs) = rule.find_node_mut("backendRefs") {
                    for backend in &mut backend_refs.children {
                        if backend.find_node("port").is_none() {
                            let indent = backend.indent + 2;
                            backend.children.push(SemanticNode {
                                key: "port".to_string(),
                                value: Some("443".to_string()),
                                indent,
                                is_empty_flow: false,
                                shards: vec![NativeShard {
                                    key: "port".to_string(),
                                    value: Some("443".to_string()),
                                    indent,
                                    original_indent: indent,
                                    raw_line: format!("{}port: 443", " ".repeat(indent)),
                                    ..Default::default()
                                }],
                                children: Vec::new(),
                            });
                            let msg = format!(
                                "Remediation [{}]: Injected default port 443 for TLSRoute '{}' backendRef.",
                                GATEWAY_API_TLS_RULE_ID, route_name
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }
        }
    }

    changes
}

/// Heals Gateway API `BackendTLSPolicy` resources by normalizing targetRef API groups,
/// aligning CA certificate references to core ConfigMaps, and realigning SAN hostnames.
pub fn heal_backend_tls_policies(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "BackendTLSPolicy" {
        return changes;
    }

    let policy_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-policy".to_string());
    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let mut target_service = None;

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        // 1. Align targetRefs group
        if let Some(target_refs) = spec.find_node_mut("targetRefs") {
            for target in &mut target_refs.children {
                if let Some(svc_name) = target.find_value("name") {
                    target_service = Some(svc_name);
                }
                if let Some(grp_node) = target.find_node_mut("group") {
                    let grp_val = grp_node.value.clone().unwrap_or_default();
                    let clean_grp = grp_val.trim_matches('"').trim_matches('\'');
                    if clean_grp == "core" || clean_grp == "v1" {
                        grp_node.value = Some("\"\"".to_string());
                        for s in &mut grp_node.shards {
                            s.value = Some("\"\"".to_string());
                        }
                        let msg = format!(
                            "Remediation [{}]: Normalized BackendTLSPolicy '{}' targetRef group '{}' -> empty string for core Service.",
                            BACKEND_TLS_POLICY_RULE_ID, policy_name, clean_grp
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }

        // 2. Align spec.tls caCertificateRefs and hostname
        if let Some(tls) = spec.find_node_mut("tls") {
            if let Some(ca_refs) = tls.find_node_mut("caCertificateRefs") {
                for ca in &mut ca_refs.children {
                    if let Some(grp_node) = ca.find_node_mut("group") {
                        let grp_val = grp_node.value.clone().unwrap_or_default();
                        let clean_grp = grp_val.trim_matches('"').trim_matches('\'');
                        if clean_grp == "core" || clean_grp == "v1" {
                            grp_node.value = Some("\"\"".to_string());
                            for s in &mut grp_node.shards {
                                s.value = Some("\"\"".to_string());
                            }
                            let msg = format!(
                                "Remediation [{}]: Normalized BackendTLSPolicy '{}' caCertificateRef group to empty string.",
                                BACKEND_TLS_POLICY_RULE_ID, policy_name
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                    if ca.find_node("kind").is_none() {
                        let indent = ca.indent + 2;
                        ca.children.push(SemanticNode {
                            key: "kind".to_string(),
                            value: Some("ConfigMap".to_string()),
                            indent,
                            is_empty_flow: false,
                            shards: vec![NativeShard {
                                key: "kind".to_string(),
                                value: Some("ConfigMap".to_string()),
                                indent,
                                original_indent: indent,
                                raw_line: format!("{}kind: ConfigMap", " ".repeat(indent)),
                                ..Default::default()
                            }],
                            children: Vec::new(),
                        });
                        let msg = format!(
                            "Remediation [{}]: Injected default 'kind: ConfigMap' for BackendTLSPolicy '{}' caCertificateRef.",
                            BACKEND_TLS_POLICY_RULE_ID, policy_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }

            // 3. Service SAN Hostname alignment
            if let Some(svc) = target_service {
                let canonical_hostname = format!("{}.{}.svc.cluster.local", svc, ns);
                if let Some(host_node) = tls.find_node_mut("hostname") {
                    let cur_host = host_node.value.clone().unwrap_or_default();
                    let clean_host = cur_host.trim().trim_matches('"').trim_matches('\'');
                    if clean_host.is_empty() || clean_host == "localhost" || clean_host == "backend"
                    {
                        host_node.value = Some(canonical_hostname.clone());
                        for s in &mut host_node.shards {
                            s.value = Some(canonical_hostname.clone());
                        }
                        let msg = format!(
                            "Remediation [{}]: Realigned BackendTLSPolicy '{}' TLS hostname SAN to '{}'.",
                            BACKEND_TLS_POLICY_RULE_ID, policy_name, canonical_hostname
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                } else {
                    let indent = tls.indent + 2;
                    tls.children.push(SemanticNode {
                        key: "hostname".to_string(),
                        value: Some(canonical_hostname.clone()),
                        indent,
                        is_empty_flow: false,
                        shards: vec![NativeShard {
                            key: "hostname".to_string(),
                            value: Some(canonical_hostname.clone()),
                            indent,
                            original_indent: indent,
                            raw_line: format!(
                                "{}hostname: {}",
                                " ".repeat(indent),
                                canonical_hostname
                            ),
                            ..Default::default()
                        }],
                        children: Vec::new(),
                    });
                    let msg = format!(
                        "Remediation [{}]: Injected canonical BackendTLSPolicy '{}' TLS hostname SAN '{}'.",
                        BACKEND_TLS_POLICY_RULE_ID, policy_name, canonical_hostname
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

    #[test]
    fn test_tls_route_passthrough_validation() {
        // Test healing a TLSRoute that lacks port in backendRefs
        let route_yaml = r#"
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TLSRoute
metadata:
  name: edge-tls
  namespace: default
spec:
  rules:
    - backendRefs:
        - name: edge-svc
"#;
        let mut route_parsed =
            crate::structurer::native_structurize(crate::sharder::native_shard(route_yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_tls_routes(&mut route_parsed, &mut telemetry);
        assert!(!changes.is_empty());
        let reconstructed =
            crate::parsers::reconstructor::native_reconstruct_from_semantic(&route_parsed);
        assert!(reconstructed.contains("port: 443"));
    }

    #[test]
    fn test_tls_route_sni_hostname_repair() {
        let yaml = r#"
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TLSRoute
metadata:
  name: my-tls-route
  namespace: default
spec:
  hostnames:
    - "SECURE.EXAMPLE.COM."
  rules:
    - backendRefs:
        - name: my-svc
          port: 443
"#;
        let mut parsed = crate::structurer::native_structurize(crate::sharder::native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_tls_routes(&mut parsed, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("Sanitized TLSRoute"));
        let reconstructed =
            crate::parsers::reconstructor::native_reconstruct_from_semantic(&parsed);
        assert!(reconstructed.contains("\"secure.example.com\""));
    }

    #[test]
    fn test_backend_tls_policy_ca_cert_alignment() {
        let yaml = r#"
apiVersion: gateway.networking.k8s.io/v1alpha3
kind: BackendTLSPolicy
metadata:
  name: auth-backend-tls
  namespace: prod
spec:
  targetRefs:
    - group: "core"
      kind: Service
      name: auth-service
  tls:
    caCertificateRefs:
      - group: "core"
        name: auth-ca-cert
"#;
        let mut parsed = crate::structurer::native_structurize(crate::sharder::native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_backend_tls_policies(&mut parsed, &mut telemetry);
        assert!(changes.len() >= 2);
        let reconstructed =
            crate::parsers::reconstructor::native_reconstruct_from_semantic(&parsed);
        assert!(reconstructed.contains("kind: ConfigMap"));
        assert!(reconstructed.contains("auth-service.prod.svc.cluster.local"));
    }
}
