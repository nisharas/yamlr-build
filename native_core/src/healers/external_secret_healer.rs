//! ExternalSecret Target & SecretStore Reference Healer (Rule SEC-009).
//!
//! Why: In ExternalSecrets (`external-secrets.io`), typos in `secretStoreRef.name` or a missing
//! `target.name` prevent Kubernetes Secret synthesis from cloud providers (AWS, GCP, Vault),
//! causing dependent pods to crash.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const EXTERNAL_SECRET_RULE_ID: &str = "SEC-009";
pub const STORE_SIMILARITY_THRESHOLD: f64 = 0.70;

/// Aligns ExternalSecret secretStoreRef and synthesizes missing target definitions.
pub fn heal_external_secrets(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "ExternalSecret" {
        return changes;
    }

    let es_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-external-secret".to_string());

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let stores: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| {
            (id.kind == "SecretStore" && (id.namespace == ns || id.namespace.is_empty()))
                || id.kind == "ClusterSecretStore"
        })
        .collect();

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        // 1. Check and heal secretStoreRef
        if let Some(store_ref) = spec.find_node_mut("secretStoreRef") {
            let current_name = store_ref.find_value("name").unwrap_or_default();
            let clean_name = current_name.trim().trim_matches('"').trim_matches('\'');

            if !clean_name.is_empty()
                && !stores.iter().any(|s| s.name == clean_name)
                && !stores.is_empty()
            {
                let mut best_target = None;
                let mut best_ratio = 0.0;
                for s in &stores {
                    let ratio =
                        crate::healers::selector_healer::similarity_ratio(clean_name, &s.name);
                    if ratio >= STORE_SIMILARITY_THRESHOLD && ratio > best_ratio {
                        best_ratio = ratio;
                        best_target = Some((*s).clone());
                    }
                }

                if let Some(target) = best_target {
                    if let Some(name_node) = store_ref.find_node_mut("name") {
                        name_node.value = Some(target.name.clone());
                        for s in &mut name_node.shards {
                            s.value = Some(target.name.clone());
                        }
                    }
                    if let Some(kind_node) = store_ref.find_node_mut("kind") {
                        kind_node.value = Some(target.kind.clone());
                    }
                    let msg = format!(
                        "Remediation [{}]: Aligned ExternalSecret secretStoreRef '{}' -> '{}' ({}) (similarity: {:.2}).",
                        EXTERNAL_SECRET_RULE_ID, clean_name, target.name, target.kind, best_ratio
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }

        // 2. Synthesize missing target.name
        if let Some(target_node) = spec.find_node_mut("target") {
            if target_node.find_value("name").is_none() {
                let indent = target_node.indent + 2;
                target_node.children.push(SemanticNode {
                    key: "name".to_string(),
                    value: Some(es_name.clone()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent,
                    is_empty_flow: false,
                });
                let msg = format!(
                    "Remediation [{}]: Injected target.name: '{}' into ExternalSecret '{}'.",
                    EXTERNAL_SECRET_RULE_ID, es_name, es_name
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        } else {
            let indent = spec.indent + 2;
            spec.children.push(SemanticNode {
                key: "target".to_string(),
                value: None,
                children: vec![SemanticNode {
                    key: "name".to_string(),
                    value: Some(es_name.clone()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: indent + 2,
                    is_empty_flow: false,
                }],
                shards: Vec::new(),
                indent,
                is_empty_flow: false,
            });
            let msg = format!(
                "Remediation [{}]: Synthesized target definition with name: '{}' for ExternalSecret.",
                EXTERNAL_SECRET_RULE_ID, es_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_synthesize_target_name() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("ExternalSecret".into()),
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
                            value: Some("db-creds".into()),
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
                        children: vec![],
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
        let changes = heal_external_secrets(&mut manifest, &[], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        let target = spec.find_node("target").unwrap();
        assert_eq!(target.find_value("name"), Some("db-creds".to_string()));
    }
}
