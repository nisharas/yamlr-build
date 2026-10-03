//! Secret Reference Alignment Healer (Rule REF-004).
//!
//! Why: Misspelled Secret references across `env[].valueFrom.secretKeyRef`, `envFrom[].secretRef`,
//! `volumes[].secret.secretName`, and `imagePullSecrets[].name` trigger `CreateContainerConfigError`
//! or `ImagePullBackOff` authentication failures.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const SECRET_REF_RULE_ID: &str = "REF-004";
pub const SECRET_SIMILARITY_THRESHOLD: f64 = 0.70;

/// Recursively aligns Secret references in an AST node tree.
fn align_secrets_recursive(
    node: &mut SemanticNode,
    ns: &str,
    secrets: &[&NativeIdentity],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let key_lower = node.key.to_lowercase();

    // 1. env[].valueFrom.secretKeyRef or envFrom[].secretRef
    if key_lower == "secretref" || key_lower == "secretkeyref" {
        if let Some(name_node) = node.find_node_mut("name") {
            align_secret_name_node(name_node, ns, secrets, "env secretRef", telemetry, changes);
        }
    }

    // 2. volumes[].secret.secretName
    if key_lower == "secret" {
        if let Some(name_node) = node.find_node_mut("secretName") {
            align_secret_name_node(
                name_node,
                ns,
                secrets,
                "volume secretName",
                telemetry,
                changes,
            );
        }
    }

    // 3. imagePullSecrets[].name
    if key_lower == "imagepullsecrets" {
        for secret_item in &mut node.children {
            if let Some(name_node) = secret_item.find_node_mut("name") {
                align_secret_name_node(
                    name_node,
                    ns,
                    secrets,
                    "imagePullSecrets",
                    telemetry,
                    changes,
                );
            }
        }
    }

    for child in &mut node.children {
        align_secrets_recursive(child, ns, secrets, telemetry, changes);
    }
}

fn align_secret_name_node(
    name_node: &mut SemanticNode,
    ns: &str,
    secrets: &[&NativeIdentity],
    context_desc: &str,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let current = name_node.value.clone().unwrap_or_default();
    let clean = current.trim().trim_matches('"').trim_matches('\'');

    if !clean.is_empty() && !secrets.iter().any(|s| s.name == clean) && !secrets.is_empty() {
        let mut best_target = None;
        let mut best_ratio = 0.0;
        for s in secrets {
            // Check exact match or Kustomize generated hash match (e.g. app-secret-g8b5m297kd -> app-secret)
            let is_kustomize_match = s.name.len() == clean.len() + 11
                && s.name.starts_with(clean)
                && s.name.chars().nth(clean.len()) == Some('-')
                && s.name[clean.len() + 1..]
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric());

            if is_kustomize_match {
                best_target = Some(s.name.clone());
                best_ratio = 1.0;
                break;
            }

            let ratio = crate::healers::selector_healer::similarity_ratio(clean, &s.name);
            if ratio >= SECRET_SIMILARITY_THRESHOLD && ratio > best_ratio {
                best_ratio = ratio;
                best_target = Some(s.name.clone());
            }
        }

        if let Some(target) = best_target {
            name_node.value = Some(target.clone());
            for s in &mut name_node.shards {
                s.value = Some(target.clone());
            }
            let msg = format!(
                "Remediation [{}]: Aligned {} '{}' -> '{}' in namespace '{}' (similarity: {:.2}).",
                SECRET_REF_RULE_ID, context_desc, clean, target, ns, best_ratio
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }
}

/// Primary Entrypoint: Aligns all broken Secret references in a manifest against known identities.
pub fn heal_secret_references(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let secrets: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| {
            id.kind == "Secret"
                && (id.namespace == ns || id.namespace.is_empty() || id.namespace == "default")
        })
        .collect();

    align_secrets_recursive(&mut manifest.root, &ns, &secrets, telemetry, &mut changes);
    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_align_volume_secret_name_typo() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![SemanticNode {
                    key: "secret".into(),
                    value: None,
                    children: vec![SemanticNode {
                        key: "secretName".into(),
                        value: Some("db-passwrd".into()),
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
            indent_step: 2,
            integrity_violations: vec![],
        };

        let target_sec = NativeIdentity {
            kind: "Secret".into(),
            name: "db-password".into(),
            namespace: "default".into(),
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_secret_references(&mut manifest, &[target_sec], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let sec_node = manifest.root.find_node("secret").unwrap();
        assert_eq!(
            sec_node.find_value("secretName"),
            Some("db-password".to_string())
        );
    }

    #[test]
    fn test_align_kustomize_hashed_secret() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![SemanticNode {
                    key: "secret".into(),
                    value: None,
                    children: vec![SemanticNode {
                        key: "secretName".into(),
                        value: Some("app-secret".into()),
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
            indent_step: 2,
            integrity_violations: vec![],
        };

        // Kustomize generated secret with 10-char hash suffix
        let target_sec = NativeIdentity {
            kind: "Secret".into(),
            name: "app-secret-g8b5m297kd".into(),
            namespace: "default".into(),
            ..Default::default()
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_secret_references(&mut manifest, &[target_sec], &mut telemetry);
        assert_eq!(changes.len(), 1);
        let sec_node = manifest.root.find_node("secret").unwrap();
        assert_eq!(
            sec_node.find_value("secretName"),
            Some("app-secret-g8b5m297kd".to_string())
        );
    }
}
