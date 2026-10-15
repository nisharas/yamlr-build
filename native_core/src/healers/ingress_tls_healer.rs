//! Ingress TLS Secret Reference Alignment Healer (Rule NET-010).
//!
//! Why: In an Ingress manifest, typos in `spec.tls[].secretName` prevent the Ingress controller
//! from mounting the TLS certificate, falling back to a self-signed 'Fake Certificate' and triggering
//! terrifying browser security warnings for end users.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const INGRESS_TLS_RULE_ID: &str = "NET-010";
pub const TLS_SIMILARITY_THRESHOLD: f64 = 0.70;

/// Aligns or synthesizes Ingress TLS secretName against known Secret identities.
pub fn heal_ingress_tls_secrets(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Ingress" {
        return changes;
    }

    let ing_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed-ingress".to_string());

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let effective_ns = if ns.is_empty() { "default" } else { &ns };
    let secrets: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| {
            let target_ns = if id.namespace.is_empty() { "default" } else { &id.namespace };
            id.kind == "Secret" && target_ns == effective_ns
        })
        .collect();

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(tls_node) = spec.find_node_mut("tls") {
            for item in &mut tls_node.children {
                if let Some(sec_node) = item.find_node_mut("secretName") {
                    let current = sec_node.value.clone().unwrap_or_default();
                    let clean = current.trim().trim_matches('"').trim_matches('\'');

                    if !clean.is_empty()
                        && !secrets.iter().any(|s| s.name == clean)
                        && !secrets.is_empty()
                    {
                        let mut best_target = None;
                        let mut best_ratio = 0.0;
                        for s in &secrets {
                            let ratio =
                                crate::healers::selector_healer::similarity_ratio(clean, &s.name);
                            if ratio >= TLS_SIMILARITY_THRESHOLD && ratio > best_ratio {
                                best_ratio = ratio;
                                best_target = Some(s.name.clone());
                            }
                        }

                        if let Some(target) = best_target {
                            sec_node.value = Some(target.clone());
                            for s in &mut sec_node.shards {
                                s.value = Some(target.clone());
                            }
                            let msg = format!(
                                "Remediation [{}]: Aligned Ingress '{}' TLS secretName '{}' -> '{}' (similarity: {:.2}).",
                                INGRESS_TLS_RULE_ID, ing_name, clean, target, best_ratio
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                } else {
                    // Check if hosts are defined, synthesize secretName: <host>-tls
                    let first_host = item
                        .find_node("hosts")
                        .and_then(|h| h.children.first())
                        .and_then(|c| c.value.as_deref().or(Some(&c.key)))
                        .map(|h| {
                            h.trim()
                                .trim_start_matches('-')
                                .trim()
                                .trim_matches('"')
                                .trim_matches('\'')
                                .replace('.', "-")
                        });

                    if let Some(h) = first_host {
                        let synth_name = format!("{}-tls", h);
                        let indent = item.indent + 2;
                        item.children.push(SemanticNode {
                            key: "secretName".to_string(),
                            value: Some(synth_name.clone()),
                            children: Vec::new(),
                            shards: Vec::new(),
                            indent,
                            is_empty_flow: false,
                        });
                        let msg = format!(
                            "Remediation [{}]: Injected missing TLS secretName: '{}' for Ingress '{}'.",
                            INGRESS_TLS_RULE_ID, synth_name, ing_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
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
    fn test_align_ingress_tls_secret_typo() {
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
                        key: "spec".into(),
                        value: None,
                        children: vec![SemanticNode {
                            key: "tls".into(),
                            value: None,
                            children: vec![SemanticNode {
                                key: "-".into(),
                                value: None,
                                children: vec![SemanticNode {
                                    key: "secretName".into(),
                                    value: Some("app-crt-secret".into()),
                                    children: vec![],
                                    shards: vec![],
                                    indent: 6,
                                    is_empty_flow: false,
                                }],
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

        let target_sec = NativeIdentity {
            kind: "Secret".into(),
            name: "app-cert-secret".into(),
            namespace: "default".into(),
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_ingress_tls_secrets(&mut manifest, &[target_sec], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let spec = manifest.root.find_node("spec").unwrap();
        let tls = spec.find_node("tls").unwrap();
        let item = &tls.children[0];
        assert_eq!(
            item.find_value("secretName"),
            Some("app-cert-secret".to_string())
        );
    }
}
