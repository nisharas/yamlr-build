//! Crossplane Composition & XRD Auto-Healer (Rule ECO-005).
//!
//! Why: Crossplane (`apiextensions.crossplane.io/v1`) Compositions and CompositeResourceDefinitions
//! require strict field path references (`fromFieldPath: spec.parameters.region` without leading dots)
//! and explicit patch types. Omitting patch types or misconfiguring XRD domain groups blocks Crossplane
//! reconciliation and breaks multi-cloud resource provisioning.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const CROSSPLANE_RULE_ID: &str = "ECO-005";

/// Primary entrypoint: Heals Crossplane Composition and XRD manifests.
pub fn heal_crossplane_manifests(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    if !api_version.starts_with("apiextensions.crossplane.io") {
        return changes;
    }

    match kind.as_str() {
        "Composition" => changes.extend(heal_composition(manifest, telemetry)),
        "CompositeResourceDefinition" => changes.extend(heal_xrd(manifest, telemetry)),
        _ => {}
    }

    changes
}

fn heal_composition(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let spec = match manifest.root.find_node_mut("spec") {
        Some(s) => s,
        None => return changes,
    };

    // 1. Inspect resources[].patches[]
    for res_list in spec.find_nodes_by_key_recursive_mut("resources") {
        for res_item in &mut res_list.children {
            if let Some(patches_node) = res_item.find_node_mut("patches") {
                for patch in &mut patches_node.children {
                    // A. Strip leading dots on fromFieldPath and toFieldPath
                    for path_field in &["fromFieldPath", "toFieldPath"] {
                        if let Some(field_node) = patch.find_node_mut(path_field) {
                            let mut needs_strip = false;
                            let mut cleaned = String::new();
                            if let Some(ref val) = field_node.value {
                                let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
                                if clean.starts_with('.') {
                                    needs_strip = true;
                                    cleaned = clean.trim_start_matches('.').to_string();
                                }
                            }
                            if needs_strip {
                                field_node.value = Some(cleaned.clone());
                                for s in &mut field_node.shards {
                                    s.value = Some(cleaned.clone());
                                }
                                let msg = format!(
                                    "Remediation [{}]: Stripped invalid leading dot from Crossplane patch '{}' -> '{}'.",
                                    CROSSPLANE_RULE_ID, path_field, cleaned
                                );
                                native_record_healing_impact(telemetry, &msg);
                                changes.push(msg);
                            }
                        }
                    }

                    // B. Inject default patch type: FromCompositeFieldPath if omitted
                    let has_from = patch.find_node("fromFieldPath").is_some();
                    let has_to = patch.find_node("toFieldPath").is_some();
                    if has_from && has_to && patch.find_node("type").is_none() {
                        let indent = patch.indent + 2;
                        patch.children.push(SemanticNode {
                            key: "type".to_string(),
                            value: Some("FromCompositeFieldPath".to_string()),
                            children: Vec::new(),
                            shards: Vec::new(),
                            indent,
                            is_empty_flow: false,
                        });
                        let msg = format!(
                            "Remediation [{}]: Injected explicit 'type: FromCompositeFieldPath' on Crossplane patch.",
                            CROSSPLANE_RULE_ID
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

fn heal_xrd(manifest: &mut SemanticManifest, telemetry: &mut NativeTelemetry) -> Vec<String> {
    let mut changes = Vec::new();
    let spec = match manifest.root.find_node_mut("spec") {
        Some(s) => s,
        None => return changes,
    };

    // Ensure group contains a domain dot (e.g. "database" -> "database.crossplane.io")
    if let Some(group_node) = spec.find_node_mut("group") {
        let mut needs_fix = None;
        if let Some(ref val) = group_node.value {
            let clean = val.trim().trim_matches(|c| c == '\'' || c == '"');
            if !clean.contains('.') && !clean.is_empty() {
                let fq_group = format!("{}.crossplane.io", clean);
                needs_fix = Some((clean.to_string(), fq_group));
            }
        }

        if let Some((old_g, new_g)) = needs_fix {
            group_node.value = Some(new_g.clone());
            for s in &mut group_node.shards {
                s.value = Some(new_g.clone());
            }
            let msg = format!(
                "Remediation [{}]: Normalized bare XRD group '{}' -> FQDN domain '{}'.",
                CROSSPLANE_RULE_ID, old_g, new_g
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
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_heal_crossplane_composition_patch_dot_and_type() {
        let yaml = r#"
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: xpostgres.aws.database.example.org
spec:
  compositeTypeRef:
    apiVersion: database.example.org/v1alpha1
    kind: XPostgreSQLInstance
  resources:
    - name: rdsInstance
      base:
        apiVersion: database.aws.crossplane.io/v1beta1
        kind: RDSInstance
      patches:
        - fromFieldPath: .spec.parameters.storageGB
          toFieldPath: spec.forProvider.allocatedStorage
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_crossplane_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 2);
        assert!(changes[0].contains("Stripped invalid leading dot"));
        assert!(changes[1].contains("Injected explicit 'type: FromCompositeFieldPath'"));
    }

    #[test]
    fn test_heal_crossplane_xrd_group_domain() {
        let yaml = r#"
apiVersion: apiextensions.crossplane.io/v1
kind: CompositeResourceDefinition
metadata:
  name: xdatabases.example
spec:
  group: example
  names:
    kind: XDatabase
    plural: xdatabases
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_crossplane_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 1);
        assert_eq!(
            manifest.root.find_node("spec").unwrap().find_value("group"),
            Some("example.crossplane.io".to_string())
        );
    }
}
