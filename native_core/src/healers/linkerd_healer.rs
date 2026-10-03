//! Linkerd Service Mesh Policy & Profile Auto-Healer (Rule ECO-002).
//!
//! Why: Linkerd zero-trust policy resources (`policy.linkerd.io/v1beta1` Server,
//! ServerAuthorization, AuthorizationPolicy) and `linkerd.io/v1alpha2` ServiceProfiles
//! require strict proxyProtocol casing (`gRPC`, `HTTP/1`, `HTTP/2`) and fully-qualified
//! ServiceProfile names (`<svc>.<ns>.svc.cluster.local`). Invalid proxy protocols or
//! missing timeouts on retryable routes cause Linkerd micro-proxy connection resets.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const LINKERD_RULE_ID: &str = "ECO-002";

/// Primary entrypoint: Heals Linkerd zero-trust Server policies and ServiceProfile routes.
pub fn heal_linkerd_manifests(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    // Fast return if not Linkerd policy or service profile
    if !api_version.starts_with("policy.linkerd.io") && !api_version.starts_with("linkerd.io") {
        return changes;
    }

    match kind.as_str() {
        "Server" => changes.extend(heal_server(manifest, telemetry)),
        "ServiceProfile" => changes.extend(heal_service_profile(manifest, telemetry)),
        _ => {}
    }

    changes
}

fn heal_server(manifest: &mut SemanticManifest, telemetry: &mut NativeTelemetry) -> Vec<String> {
    let mut changes = Vec::new();
    let spec = match manifest.root.find_node_mut("spec") {
        Some(s) => s,
        None => return changes,
    };

    // Normalize proxyProtocol: "HTTP/1", "HTTP/2", "gRPC", "opaque", "TLS"
    if let Some(proto_node) = spec.find_node_mut("proxyProtocol") {
        let mut needs_fix = None;
        if let Some(ref val) = proto_node.value {
            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
            let lower = clean.to_lowercase();
            let canonical = match lower.as_str() {
                "grpc" => "gRPC",
                "http/1" | "http1" | "http/1.1" => "HTTP/1",
                "http/2" | "http2" => "HTTP/2",
                "opaque" => "opaque",
                "tls" => "TLS",
                _ => "",
            };

            if !canonical.is_empty() && clean != canonical {
                needs_fix = Some((clean.to_string(), canonical.to_string()));
            }
        }

        if let Some((old_val, new_val)) = needs_fix {
            proto_node.value = Some(new_val.clone());
            for s in &mut proto_node.shards {
                s.value = Some(new_val.clone());
            }
            let msg = format!(
                "Remediation [{}]: Normalized Linkerd Server proxyProtocol '{}' -> '{}'.",
                LINKERD_RULE_ID, old_val, new_val
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

fn heal_service_profile(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    // 1. Ensure metadata.name has .svc.cluster.local suffix if it's a bare service name
    if let Some(meta) = manifest.root.find_node_mut("metadata") {
        let ns = meta
            .find_value("namespace")
            .unwrap_or_else(|| "default".to_string());
        if let Some(name_node) = meta.find_node_mut("name") {
            let mut needs_fix = None;
            if let Some(ref val) = name_node.value {
                let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                if !clean.contains('.') {
                    let fqdn = format!("{}.{}.svc.cluster.local", clean, ns);
                    needs_fix = Some((clean.to_string(), fqdn));
                }
            }

            if let Some((old_name, new_name)) = needs_fix {
                name_node.value = Some(new_name.clone());
                for s in &mut name_node.shards {
                    s.value = Some(new_name.clone());
                }
                let msg = format!(
                    "Remediation [{}]: Expanded bare ServiceProfile name '{}' -> FQDN '{}'.",
                    LINKERD_RULE_ID, old_name, new_name
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    // 2. Ensure retryable routes have a timeout configured
    if let Some(spec) = manifest.root.find_node_mut("spec") {
        for routes_node in spec.find_nodes_by_key_recursive_mut("routes") {
            for route_item in &mut routes_node.children {
                let is_retryable = route_item
                    .find_value("isRetryable")
                    .map(|v| v.trim() == "true")
                    .unwrap_or(false);

                if is_retryable && route_item.find_node("timeout").is_none() {
                    let indent = route_item.indent + 2;
                    route_item.children.push(SemanticNode {
                        key: "timeout".to_string(),
                        value: Some("10s".to_string()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent,
                        is_empty_flow: false,
                    });
                    let msg = format!(
                        "Remediation [{}]: Injected default 'timeout: 10s' for retryable route in ServiceProfile.",
                        LINKERD_RULE_ID
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
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_heal_linkerd_server_proxy_protocol() {
        let yaml = r#"
apiVersion: policy.linkerd.io/v1beta1
kind: Server
metadata:
  name: admin-server
spec:
  port: 8080
  proxyProtocol: grpc
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_linkerd_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("proxyProtocol 'grpc' -> 'gRPC'"));
    }

    #[test]
    fn test_heal_service_profile_name_and_retry_timeout() {
        let yaml = r#"
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: authors
  namespace: books
spec:
  routes:
    - name: GetAuthor
      isRetryable: true
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_linkerd_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 2);
        assert!(changes[0].contains(
            "Expanded bare ServiceProfile name 'authors' -> FQDN 'authors.books.svc.cluster.local'"
        ));
        assert!(changes[1].contains("Injected default 'timeout: 10s'"));
    }
}
