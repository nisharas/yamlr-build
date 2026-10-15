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
    if node.key == "data" || node.key == "stringData" || node.key == "binaryData" {
        return;
    }

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
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

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

    // Trap 57 / Rule SEC-022: Normalize scalar or list shapes in imagePullSecrets
    let ips_changes = heal_image_pull_secrets_shapes(&mut manifest.root, telemetry);
    changes.extend(ips_changes);

    // Trap 47 / Rule SEC-021: Normalize secret volume `name:` collision into canonical `secretName:`
    let sec_vol_changes = heal_secret_volume_name_keys(&mut manifest.root, telemetry);
    changes.extend(sec_vol_changes);

    align_secrets_recursive(&mut manifest.root, &ns, &secrets, telemetry, &mut changes);

    changes
}

pub const RULE_SEC_022: &str = "SEC-022";

/// Rule SEC-022 (Trap 57): Normalizes scalar string or string list in `spec.imagePullSecrets` to canonical `LocalObjectReference` sequence.
///
/// Why: Under `PodSpec.imagePullSecrets`, the official OpenAPI schema strictly expects `[]LocalObjectReference` (`- name: <secret-name>`).
/// Developers frequently write:
/// 1. `imagePullSecrets: my-secret` (scalar string)
/// 2. `imagePullSecrets:\n  - my-secret` (list of scalar strings)
/// Kube-apiserver immediately rejects this with:
/// `Invalid value: "string": expected map[string]interface{}`.
/// This healer normalizes all scalar string entries into `- name: <secret-name>`.
pub fn heal_image_pull_secrets_shapes(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    heal_image_pull_secrets_shapes_recursive(node, telemetry, &mut changes);
    changes
}

fn heal_image_pull_secrets_shapes_recursive(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "imagePullSecrets" {
        let p_indent = node.indent;

        // Case 1: imagePullSecrets is a scalar value (e.g. `imagePullSecrets: my-secret`)
        let scalar_clone = node.value.clone();
        if let Some(scalar_val) = scalar_clone {
            let clean = scalar_val.trim().trim_matches(|c| c == '\'' || c == '"');
            if !clean.is_empty() {
                let secret_name = clean.to_string();
                node.value = None;
                for s in &mut node.shards {
                    s.value = None;
                }

                let new_child = SemanticNode {
                    key: "-".to_string(),
                    value: None,
                    indent: p_indent + 2,
                    is_empty_flow: false,
                    children: vec![SemanticNode {
                        key: "name".to_string(),
                        value: Some(secret_name.clone()),
                        indent: p_indent + 4,
                        is_empty_flow: false,
                        children: Vec::new(),
                        shards: Vec::new(),
                    }],
                    shards: Vec::new(),
                };
                node.children = vec![new_child];

                let msg = format!(
                    "Remediation [{}]: Converted scalar 'imagePullSecrets: {}' to canonical sequence item '- name: {}'.",
                    RULE_SEC_022, scalar_val, secret_name
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        } else {
            // Case 2: imagePullSecrets is a sequence, but items are scalar strings instead of maps with `name:`
            for item in &mut node.children {
                if item.key == "name" {
                    // Already a valid list item with `name:` key!
                    continue;
                }
                let item_val_clone = item.value.clone();
                if let Some(val) = item_val_clone {
                    let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                    if !clean.is_empty() && item.children.is_empty() {
                        let secret_name = clean.to_string();
                        let new_child = SemanticNode {
                            key: "name".to_string(),
                            value: Some(secret_name.clone()),
                            indent: item.indent + 2,
                            is_empty_flow: false,
                            children: Vec::new(),
                            shards: Vec::new(),
                        };
                        item.key = "-".to_string();
                        item.value = None;
                        item.shards.clear();
                        item.children = vec![new_child];

                        let msg = format!(
                            "Remediation [{}]: Converted scalar list item '- {}' under 'imagePullSecrets' to '- name: {}'.",
                            RULE_SEC_022, val, secret_name
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    }

    for child in &mut node.children {
        heal_image_pull_secrets_shapes_recursive(child, telemetry, changes);
    }
}

/// Rule SEC-021 (Trap 47): Heals `name:` collisions under `spec.volumes[*].secret`.
///
/// Why: Under `spec.volumes[*].secret`, the Kubernetes OpenAPI schema strictly requires `secretName: <string>`.
/// Developers (especially those familiar with `volumes[*].configMap.name`) often mistakenly declare
/// `volumes[*].secret.name: my-secret` instead of `volumes[*].secret.secretName: my-secret`.
/// Kubernetes admission immediately rejects this: `unknown field "name" in io.k8s.api.core.v1.SecretVolumeSource`.
/// Zero-assumption: Renaming `name` to `secretName` under `secret:` is deterministic and schema-guaranteed.
pub fn heal_secret_volume_name_keys(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    heal_secret_volume_name_keys_recursive(node, telemetry, &mut changes);
    changes
}

fn heal_secret_volume_name_keys_recursive(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if node.key == "volumes" {
        for vol_item in &mut node.children {
            if let Some(sec_node) = vol_item.find_node_mut("secret") {
                let has_secret_name = sec_node.find_node("secretName").is_some();
                if !has_secret_name {
                    if let Some(name_idx) = sec_node.children.iter().position(|c| c.key == "name") {
                        let name_child = &mut sec_node.children[name_idx];
                        name_child.key = "secretName".to_string();
                        for s in &mut name_child.shards {
                            s.key = "secretName".to_string();
                        }
                        let val_str = name_child.value.clone().unwrap_or_default();
                        let msg = format!(
                            "Remediation [SEC-021]: Renamed invalid key 'secret.name' -> 'secret.secretName: {}' under volume.",
                            val_str
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    }

    for child in &mut node.children {
        heal_secret_volume_name_keys_recursive(child, telemetry, changes);
    }
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

    #[test]
    fn test_heal_secret_volume_name_key() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Deployment".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "volumes".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "-".into(),
                                value: None,
                                children: vec![
                                    SemanticNode {
                                        key: "name".into(),
                                        value: Some("secret-vol".into()),
                                        children: vec![],
                                        shards: vec![],
                                        indent: 4,
                                        is_empty_flow: false,
                                    },
                                    SemanticNode {
                                        key: "secret".into(),
                                        value: None,
                                        children: vec![
                                            SemanticNode {
                                                key: "name".into(), // Invalid key instead of secretName
                                                value: Some("db-credentials".into()),
                                                children: vec![],
                                                shards: vec![],
                                                indent: 6,
                                                is_empty_flow: false,
                                            },
                                        ],
                                        shards: vec![],
                                        indent: 4,
                                        is_empty_flow: false,
                                    },
                                ],
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
        let changes = heal_secret_references(&mut manifest, &[], &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("[SEC-021]"));

        let vols = manifest.root.find_node("volumes").unwrap();
        let sec = vols.children[0].find_node("secret").unwrap();
        assert_eq!(sec.find_value("secretName"), Some("db-credentials".to_string()));
        assert!(sec.find_node("name").is_none());
    }

    #[test]
    fn test_heal_image_pull_secrets_shapes() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "imagePullSecrets".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "-".into(),
                                value: Some("registry-secret-a".into()), // scalar item in sequence
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
        let changes = heal_secret_references(&mut manifest, &[], &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("[SEC-022]"));

        let ips = manifest.root.find_node("imagePullSecrets").unwrap();
        assert_eq!(ips.children[0].find_value("name"), Some("registry-secret-a".to_string()));
    }
}

