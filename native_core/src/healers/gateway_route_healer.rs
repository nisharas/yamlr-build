//! Gateway API GRPCRoute, TCPRoute, and TLSRoute Modernizer.
//!
//! Why: Kubernetes Ingress lacks native constructs for layer-4 TCP stream routing,
//! layer-7 gRPC method routing, and TLS passthrough routing. Envoy Gateway, Istio, and Cilium use
//! Gateway API `GRPCRoute` (v1), `TCPRoute` (v1alpha2), and `TLSRoute` (v1alpha2) to provide
//! first-class modern routing.

use crate::models::{NativeTelemetry, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub use crate::healers::gateway_tls_healer::{
    heal_backend_tls_policies, heal_tls_routes, BACKEND_TLS_POLICY_RULE_ID, GATEWAY_API_TLS_RULE_ID,
};

pub const GATEWAY_API_GRPC_RULE_ID: &str = "MIG-003";
pub const GATEWAY_API_TCP_RULE_ID: &str = "MIG-004";

#[derive(Debug, Clone)]
pub struct GrpcRouteRule {
    pub service_name: String,
    pub service_port: i32,
    pub service_method: Option<String>,
}

#[derive(Debug, Clone)]
pub struct TcpRouteRule {
    pub service_name: String,
    pub service_port: i32,
}

/// Converts a Service with `appProtocol: grpc` or port named `grpc` into a Gateway API `GRPCRoute`.
pub fn convert_service_to_grpcroute(
    node: &SemanticNode,
    telemetry: &mut NativeTelemetry,
) -> Option<String> {
    let kind = node.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return None;
    }

    let meta = node.find_node("metadata")?;
    let name = meta
        .find_value("name")
        .unwrap_or_else(|| "grpc-service".to_string());
    let ns = meta
        .find_value("namespace")
        .unwrap_or_else(|| "default".to_string());

    let spec = node.find_node("spec")?;
    let ports = spec.find_node("ports")?;

    let mut grpc_ports = Vec::new();
    for p in &ports.children {
        let app_proto = p
            .find_value("appProtocol")
            .unwrap_or_default()
            .to_lowercase();
        let port_name = p.find_value("name").unwrap_or_default().to_lowercase();
        let port_num = p
            .find_value("port")
            .and_then(|v| v.parse::<i32>().ok())
            .unwrap_or(0);

        if app_proto == "grpc" || port_name.contains("grpc") || port_num == 50051 {
            grpc_ports.push(port_num);
        }
    }

    if grpc_ports.is_empty() {
        return None;
    }

    let route_name = format!("{}-grpc-route", name);
    let mut out = String::new();
    out.push_str("apiVersion: gateway.networking.k8s.io/v1\n");
    out.push_str("kind: GRPCRoute\n");
    out.push_str("metadata:\n");
    out.push_str(&format!("  name: {}\n", route_name));
    out.push_str(&format!("  namespace: {}\n", ns));
    out.push_str("spec:\n");
    out.push_str("  rules:\n");
    for port in grpc_ports {
        out.push_str("    - backendRefs:\n");
        out.push_str(&format!("        - name: {}\n", name));
        out.push_str(&format!("          port: {}\n", port));
    }

    let msg = format!(
        "Remediation [{}]: Generated Gateway API GRPCRoute for Service '{}'.",
        GATEWAY_API_GRPC_RULE_ID, name
    );
    native_record_healing_impact(telemetry, &msg);

    Some(out)
}

/// Converts a Service with TCP stream routing (e.g. database, redis, or explicit ingress tcp-services)
/// into a Gateway API `TCPRoute`.
pub fn convert_service_to_tcproute(
    node: &SemanticNode,
    telemetry: &mut NativeTelemetry,
) -> Option<String> {
    let kind = node.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return None;
    }

    let meta = node.find_node("metadata")?;
    let name = meta
        .find_value("name")
        .unwrap_or_else(|| "tcp-service".to_string());
    let ns = meta
        .find_value("namespace")
        .unwrap_or_else(|| "default".to_string());

    let spec = node.find_node("spec")?;
    let ports = spec.find_node("ports")?;

    let mut tcp_ports = Vec::new();
    for p in &ports.children {
        let proto = p
            .find_value("protocol")
            .unwrap_or_else(|| "TCP".to_string())
            .to_uppercase();
        let port_num = p
            .find_value("port")
            .and_then(|v| v.parse::<i32>().ok())
            .unwrap_or(0);
        let port_name = p.find_value("name").unwrap_or_default().to_lowercase();

        // Flag pure non-HTTP TCP streams (redis 6379, postgres 5432, mysql 3306, kafka 9092, or name containing tcp)
        if proto == "TCP"
            && (port_name.contains("tcp")
                || port_num == 6379
                || port_num == 5432
                || port_num == 3306
                || port_num == 9092)
        {
            tcp_ports.push(port_num);
        }
    }

    if tcp_ports.is_empty() {
        return None;
    }

    let route_name = format!("{}-tcp-route", name);
    let mut out = String::new();
    out.push_str("apiVersion: gateway.networking.k8s.io/v1alpha2\n");
    out.push_str("kind: TCPRoute\n");
    out.push_str("metadata:\n");
    out.push_str(&format!("  name: {}\n", route_name));
    out.push_str(&format!("  namespace: {}\n", ns));
    out.push_str("spec:\n");
    out.push_str("  rules:\n");
    for port in tcp_ports {
        out.push_str("    - backendRefs:\n");
        out.push_str(&format!("        - name: {}\n", name));
        out.push_str(&format!("          port: {}\n", port));
    }

    let msg = format!(
        "Remediation [{}]: Generated Gateway API TCPRoute for Service '{}'.",
        GATEWAY_API_TCP_RULE_ID, name
    );
    native_record_healing_impact(telemetry, &msg);

    Some(out)
}

/// Converts a Service with TLS passthrough, appProtocol tls, or SSL port into a Gateway API `TLSRoute`.
pub fn convert_service_to_tlsroute(
    node: &SemanticNode,
    telemetry: &mut NativeTelemetry,
) -> Option<String> {
    let kind = node.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return None;
    }

    let meta = node.find_node("metadata")?;
    let name = meta
        .find_value("name")
        .unwrap_or_else(|| "tls-service".to_string());
    let ns = meta
        .find_value("namespace")
        .unwrap_or_else(|| "default".to_string());

    let spec = node.find_node("spec")?;
    let ports = spec.find_node("ports")?;

    let mut tls_ports = Vec::new();
    for p in &ports.children {
        let app_proto = p
            .find_value("appProtocol")
            .unwrap_or_default()
            .to_lowercase();
        let port_name = p.find_value("name").unwrap_or_default().to_lowercase();
        let port_num = p
            .find_value("port")
            .and_then(|v| v.parse::<i32>().ok())
            .unwrap_or(0);

        if app_proto == "tls"
            || app_proto == "ssl"
            || app_proto == "https"
            || port_name.contains("tls")
            || port_name.contains("ssl")
            || port_name.contains("https")
            || port_num == 443
            || port_num == 8443
        {
            tls_ports.push(port_num);
        }
    }

    let is_passthrough = meta
        .find_node("annotations")
        .and_then(|a| a.find_value("yamlr.dev/tls-passthrough"))
        .map(|v| v.trim_matches('"') == "true")
        .unwrap_or(false);

    if tls_ports.is_empty() && !is_passthrough {
        return None;
    }

    let target_port = if tls_ports.is_empty() {
        443
    } else {
        tls_ports[0]
    };
    let route_name = format!("{}-tls-route", name);
    let mut out = String::new();
    out.push_str("apiVersion: gateway.networking.k8s.io/v1alpha2\n");
    out.push_str("kind: TLSRoute\n");
    out.push_str("metadata:\n");
    out.push_str(&format!("  name: {}\n", route_name));
    out.push_str(&format!("  namespace: {}\n", ns));
    out.push_str("spec:\n");
    out.push_str("  hostnames:\n");
    out.push_str(&format!("    - \"{}.example.com\"\n", name));
    out.push_str("  rules:\n");
    out.push_str("    - backendRefs:\n");
    out.push_str(&format!("        - name: {}\n", name));
    out.push_str(&format!("          port: {}\n", target_port));

    let msg = format!(
        "Remediation [{}]: Generated Gateway API TLSRoute for Service '{}'.",
        GATEWAY_API_TLS_RULE_ID, name
    );
    native_record_healing_impact(telemetry, &msg);

    Some(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_convert_service_to_grpcroute() {
        let yaml = r#"
apiVersion: v1
kind: Service
metadata:
  name: order-service
  namespace: prod
spec:
  ports:
    - name: grpc
      port: 50051
      appProtocol: grpc
"#;
        let parsed = crate::structurer::native_structurize(crate::sharder::native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let grpc_yaml = convert_service_to_grpcroute(&parsed.root, &mut telemetry).unwrap();
        assert!(grpc_yaml.contains("kind: GRPCRoute"));
        assert!(grpc_yaml.contains("order-service-grpc-route"));
        assert!(grpc_yaml.contains("50051"));
    }

    #[test]
    fn test_convert_service_to_tcproute() {
        let yaml = r#"
apiVersion: v1
kind: Service
metadata:
  name: redis-leader
  namespace: prod
spec:
  ports:
    - name: redis
      port: 6379
      protocol: TCP
"#;
        let parsed = crate::structurer::native_structurize(crate::sharder::native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let tcp_yaml = convert_service_to_tcproute(&parsed.root, &mut telemetry).unwrap();
        assert!(tcp_yaml.contains("kind: TCPRoute"));
        assert!(tcp_yaml.contains("redis-leader-tcp-route"));
        assert!(tcp_yaml.contains("6379"));
    }

    #[test]
    fn test_convert_service_to_tlsroute() {
        let yaml = r#"
apiVersion: v1
kind: Service
metadata:
  name: secure-app
  namespace: prod
  annotations:
    yamlr.dev/tls-passthrough: "true"
spec:
  ports:
    - name: https
      port: 443
      appProtocol: tls
"#;
        let parsed = crate::structurer::native_structurize(crate::sharder::native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let tls_yaml = convert_service_to_tlsroute(&parsed.root, &mut telemetry).unwrap();
        assert!(tls_yaml.contains("kind: TLSRoute"));
        assert!(tls_yaml.contains("secure-app-tls-route"));
        assert!(tls_yaml.contains("secure-app.example.com"));
        assert!(tls_yaml.contains("443"));
    }
}
