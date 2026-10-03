//! cert-manager Issuer & ClusterIssuer Reference Healer (Rule SEC-008).
//!
//! Why: Misconfigurations in cert-manager `issuerRef.name` or mixing up `cert-manager.io/issuer`
//! with `cert-manager.io/cluster-issuer` prevents certificate issuance, leaving workloads with expired
//! or missing TLS certificates and triggering customer-facing downtime.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const CERT_MANAGER_RULE_ID: &str = "SEC-008";
pub const ISSUER_SIMILARITY_THRESHOLD: f64 = 0.70;

/// Aligns cert-manager issuer references in Certificate manifests and Ingress annotations.
pub fn heal_cert_manager_issuers(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let cluster_issuers: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| id.kind == "ClusterIssuer")
        .collect();

    let namespace_issuers: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| id.kind == "Issuer" && (id.namespace == ns || id.namespace.is_empty()))
        .collect();

    // 1. Ingress Annotations
    if kind == "Ingress" {
        if let Some(metadata) = manifest.root.find_node_mut("metadata") {
            if let Some(annotations) = metadata.find_node_mut("annotations") {
                // Case A: cert-manager.io/issuer pointing to a ClusterIssuer
                if let Some(issuer_node) = annotations.find_node_mut("cert-manager.io/issuer") {
                    let current_name = issuer_node.value.clone().unwrap_or_default();
                    let clean_name = current_name.trim().trim_matches('"').trim_matches('\'');

                    // If not found in namespace issuers, but exists in cluster issuers -> migrate key!
                    let in_ns = namespace_issuers.iter().any(|i| i.name == clean_name);
                    let in_cluster = cluster_issuers.iter().any(|ci| ci.name == clean_name);

                    if !in_ns && in_cluster {
                        issuer_node.key = "cert-manager.io/cluster-issuer".to_string();
                        for s in &mut issuer_node.shards {
                            s.key = "cert-manager.io/cluster-issuer".to_string();
                        }
                        let msg = format!(
                            "Remediation [{}]: Migrated annotation 'cert-manager.io/issuer' -> 'cert-manager.io/cluster-issuer' for '{}'.",
                            CERT_MANAGER_RULE_ID, clean_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    } else if !in_ns && !in_cluster {
                        // Fuzzy match across both
                        let mut best_target = None;
                        let mut best_ratio = 0.0;
                        let mut is_target_cluster = false;

                        for ci in &cluster_issuers {
                            let ratio = crate::healers::selector_healer::similarity_ratio(
                                clean_name, &ci.name,
                            );
                            if ratio >= ISSUER_SIMILARITY_THRESHOLD && ratio > best_ratio {
                                best_ratio = ratio;
                                best_target = Some(ci.name.clone());
                                is_target_cluster = true;
                            }
                        }
                        for ni in &namespace_issuers {
                            let ratio = crate::healers::selector_healer::similarity_ratio(
                                clean_name, &ni.name,
                            );
                            if ratio >= ISSUER_SIMILARITY_THRESHOLD && ratio > best_ratio {
                                best_ratio = ratio;
                                best_target = Some(ni.name.clone());
                                is_target_cluster = false;
                            }
                        }

                        if let Some(target) = best_target {
                            issuer_node.value = Some(target.clone());
                            for s in &mut issuer_node.shards {
                                s.value = Some(target.clone());
                            }
                            if is_target_cluster {
                                issuer_node.key = "cert-manager.io/cluster-issuer".to_string();
                                for s in &mut issuer_node.shards {
                                    s.key = "cert-manager.io/cluster-issuer".to_string();
                                }
                            }
                            let msg = format!(
                                "Remediation [{}]: Aligned cert-manager issuer annotation '{}' -> '{}' (similarity: {:.2}).",
                                CERT_MANAGER_RULE_ID, clean_name, target, best_ratio
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }
        }
    }

    // 2. Certificate Spec
    if kind == "Certificate" {
        if let Some(spec) = manifest.root.find_node_mut("spec") {
            if let Some(issuer_ref) = spec.find_node_mut("issuerRef") {
                let ref_kind = issuer_ref
                    .find_value("kind")
                    .unwrap_or_else(|| "Issuer".to_string());
                let current_name = issuer_ref.find_value("name").unwrap_or_default();
                let clean_name = current_name.trim().trim_matches('"').trim_matches('\'');

                let target_list = if ref_kind == "ClusterIssuer" {
                    &cluster_issuers
                } else {
                    &namespace_issuers
                };

                if !clean_name.is_empty()
                    && !target_list.iter().any(|i| i.name == clean_name)
                    && !target_list.is_empty()
                {
                    let mut best_target = None;
                    let mut best_ratio = 0.0;

                    for i in target_list {
                        let ratio =
                            crate::healers::selector_healer::similarity_ratio(clean_name, &i.name);
                        if ratio >= ISSUER_SIMILARITY_THRESHOLD && ratio > best_ratio {
                            best_ratio = ratio;
                            best_target = Some(i.name.clone());
                        }
                    }

                    if let Some(target) = best_target {
                        if let Some(name_node) = issuer_ref.find_node_mut("name") {
                            name_node.value = Some(target.clone());
                            for s in &mut name_node.shards {
                                s.value = Some(target.clone());
                            }
                            let msg = format!(
                                "Remediation [{}]: Aligned Certificate issuerRef.name '{}' -> '{}' ({}) (similarity: {:.2}).",
                                CERT_MANAGER_RULE_ID, clean_name, target, ref_kind, best_ratio
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::SemanticNode;

    #[test]
    fn test_migrate_issuer_to_cluster_issuer_annotation() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Ingress".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "annotations".into(),
                            value: None,
                            children: vec![SemanticNode {
                                key: "cert-manager.io/issuer".into(),
                                value: Some("letsencrypt-prod".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            }],
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

        let cluster_issuer = NativeIdentity {
            kind: "ClusterIssuer".into(),
            name: "letsencrypt-prod".into(),
            namespace: String::new(),
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_cert_manager_issuers(&mut manifest, &[cluster_issuer], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let meta = manifest.root.find_node("metadata").unwrap();
        let annos = meta.find_node("annotations").unwrap();
        assert!(annos.find_node("cert-manager.io/cluster-issuer").is_some());
    }
}
