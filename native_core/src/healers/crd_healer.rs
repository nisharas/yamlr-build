//! CRD Semantic Healer (Feature 10 of 15).
//!
//! Why: Popular enterprise CRDs (CertManager Certificate, Istio VirtualService,
//! Crossplane Managed Resources) fail silently or block certificate issuance and
//! routing when references drift:
//! 1. CertManager: `issuerRef.kind: Issuer` when only a `ClusterIssuer` exists.
//! 2. Istio VirtualService: `route.destination.host` typos (e.g. `web-sv` vs `web-service`).
//! 3. Crossplane: `providerConfigRef.name` typos (e.g. `defalt` vs `default`).

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub static CRD_SIMILARITY_THRESHOLD: f64 = 0.70;

/// Heals CertManager Certificate issuerRef kind mismatch (Issuer vs ClusterIssuer).
pub fn heal_cert_manager_certificate(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Certificate" {
        return;
    }

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(issuer_ref) = spec.find_node_mut("issuerRef") {
            let issuer_name = issuer_ref.find_value("name").unwrap_or_default();
            let current_kind = issuer_ref
                .find_value("kind")
                .unwrap_or_else(|| "Issuer".to_string());

            if current_kind == "Issuer" && !issuer_name.is_empty() {
                // Check if a ClusterIssuer exists with this exact name
                let has_cluster_issuer = identities
                    .iter()
                    .any(|id| id.kind == "ClusterIssuer" && id.name == issuer_name);
                let has_local_issuer = identities
                    .iter()
                    .any(|id| id.kind == "Issuer" && id.name == issuer_name);

                if has_cluster_issuer && !has_local_issuer {
                    if let Some(kind_node) = issuer_ref.find_node_mut("kind") {
                        kind_node.value = Some("ClusterIssuer".to_string());
                        for s in &mut kind_node.shards {
                            s.value = Some("ClusterIssuer".to_string());
                        }
                    } else {
                        issuer_ref.children.push(SemanticNode {
                            key: "kind".to_string(),
                            value: Some("ClusterIssuer".to_string()),
                            children: Vec::new(),
                            shards: Vec::new(),
                            indent: issuer_ref.indent + 2,
                            is_empty_flow: false,
                        });
                    }

                    let msg = format!(
                        "Remediation [CRD-001]: Corrected Certificate issuerRef.kind to 'ClusterIssuer' for '{}'.",
                        issuer_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }
}

/// Heals Istio VirtualService destination host typos against available Services.
pub fn heal_istio_virtual_service(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "VirtualService" {
        return;
    }

    let vs_ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let services: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| id.kind == "Service" && id.namespace == vs_ns)
        .collect();

    if services.is_empty() {
        return;
    }

    for dest_host_node in manifest.root.find_nodes_by_key_recursive_mut("host") {
        let current_host = dest_host_node.value.clone().unwrap_or_default();
        if !current_host.is_empty() {
            if !services.iter().any(|s| s.name == current_host) {
                let mut best_target = None;
                let mut best_ratio = 0.0;

                for s in &services {
                    let ratio =
                        crate::healers::selector_healer::similarity_ratio(&current_host, &s.name);
                    if ratio >= CRD_SIMILARITY_THRESHOLD && ratio > best_ratio {
                        best_ratio = ratio;
                        best_target = Some(s);
                    }
                }

                if let Some(target) = best_target {
                    dest_host_node.value = Some(target.name.clone());
                    for s in &mut dest_host_node.shards {
                        s.value = Some(target.name.clone());
                    }
                    let msg = format!(
                        "Remediation [CRD-002]: Corrected Istio VirtualService destination host '{}' -> '{}' (similarity: {:.2}).",
                        current_host, target.name, best_ratio
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
    }
}

/// Primary Entrypoint: Dispatches CRD semantic healing.
pub fn heal_crd_semantics(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    heal_cert_manager_certificate(manifest, identities, telemetry, &mut changes);
    heal_istio_virtual_service(manifest, identities, telemetry, &mut changes);

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heal_cert_manager_cluster_issuer() {
        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();

        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "kind".to_string(),
                        value: Some("Certificate".to_string()),
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
                        children: vec![SemanticNode {
                            key: "issuerRef".to_string(),
                            value: None,
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![
                                SemanticNode {
                                    key: "name".to_string(),
                                    value: Some("letsencrypt-prod".to_string()),
                                    indent: 4,
                                    is_empty_flow: false,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                },
                                SemanticNode {
                                    key: "kind".to_string(),
                                    value: Some("Issuer".to_string()),
                                    indent: 4,
                                    is_empty_flow: false,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                },
                            ],
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let cluster_issuer = NativeIdentity {
            kind: "ClusterIssuer".to_string(),
            api_version: Some("cert-manager.io/v1".to_string()),
            name: "letsencrypt-prod".to_string(),
            namespace: "__cluster_scoped__".to_string(),
            owner_refs: Vec::new(),
            labels: std::collections::HashMap::new(),
            selector: std::collections::HashMap::new(),
            config_refs: Vec::new(),
            secret_refs: Vec::new(),
            volume_refs: Vec::new(),
            service_refs: Vec::new(),
            role_refs: Vec::new(),
            cluster_role_refs: Vec::new(),
            service_account: None,
            shadow_fingerprint: String::new(),
            relationships: Vec::new(),
            ports: Vec::new(),
            ..Default::default()
        };

        heal_cert_manager_certificate(
            &mut manifest,
            &[cluster_issuer],
            &mut telemetry,
            &mut changes,
        );
        assert_eq!(changes.len(), 1);
        let kind_val = manifest
            .root
            .find_node("spec")
            .unwrap()
            .find_node("issuerRef")
            .unwrap()
            .find_value("kind");
        assert_eq!(kind_val, Some("ClusterIssuer".to_string()));
    }
}
