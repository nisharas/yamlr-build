//! Kustomize Overlay Renderer & Strategic Merge Engine.
//!
//! Why: Kustomize configs separate base manifests from environment overlays via
//! `kustomization.yaml`. Scanning overlays without rendering leads to missed schema
//! violations and broken cross-references. This renderer compiles bases, applies
//! transformers (namespace, namePrefix, labels), and strategic merge patches hermetically.

use super::merge_matrix::{apply_replacements, merge_strategic};
use serde::{Deserialize, Serialize};
use serde_yaml::Value;
use std::collections::HashMap;

/// Parsed `kustomization.yaml` configuration.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct KustomizationConfig {
    #[serde(default)]
    pub resources: Vec<String>,
    pub namespace: Option<String>,
    pub name_prefix: Option<String>,
    pub name_suffix: Option<String>,
    #[serde(default)]
    pub common_labels: HashMap<String, String>,
    #[serde(default)]
    pub common_annotations: HashMap<String, String>,
    #[serde(default)]
    pub patches: Vec<KustomizePatch>,
    #[serde(default)]
    pub patches_strategic_merge: Vec<String>,
    #[serde(default)]
    pub components: Vec<String>,
    #[serde(default)]
    pub replacements: Vec<KustomizeReplacement>,
}

/// Kustomize v5+ replacement configuration for cross-resource field propagation.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct KustomizeReplacement {
    pub source: Option<ReplacementSource>,
    #[serde(default)]
    pub targets: Vec<ReplacementTarget>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReplacementSource {
    pub group: Option<String>,
    pub version: Option<String>,
    pub kind: Option<String>,
    pub name: Option<String>,
    pub namespace: Option<String>,
    pub field_path: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReplacementTarget {
    pub select: Option<PatchTarget>,
    #[serde(default)]
    pub field_paths: Vec<String>,
}

/// A patch entry in `kustomization.yaml`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KustomizePatch {
    pub patch: Option<String>,
    pub path: Option<String>,
    pub target: Option<PatchTarget>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatchTarget {
    pub group: Option<String>,
    pub version: Option<String>,
    pub kind: Option<String>,
    pub name: Option<String>,
    pub namespace: Option<String>,
}

/// Renders a collection of base resource YAML strings using the provided kustomization YAML.
///
/// Why: Provides an in-memory, deterministic compiler for Kustomize overlays.
pub fn render_kustomization(
    kustomization_yaml: &str,
    named_resources: &[(&str, &str)],
) -> Result<String, String> {
    let config: KustomizationConfig = serde_yaml::from_str(kustomization_yaml)
        .map_err(|e| format!("Failed to parse kustomization.yaml: {}", e))?;

    let mut rendered_docs: Vec<Value> = Vec::new();

    // 1. Ingest all base resources (support multi-document YAMLs)
    for (_filename, content) in named_resources {
        for document in serde_yaml::Deserializer::from_str(content) {
            let doc_val: Value = Value::deserialize(document)
                .map_err(|e| format!("Failed to parse resource YAML: {}", e))?;
            if !doc_val.is_null() {
                rendered_docs.push(doc_val);
            }
        }
    }

    // 2. Apply Strategic Merge Patches
    for patch_entry in &config.patches {
        if let Some(ref patch_str) = patch_entry.patch {
            apply_patch_string(&mut rendered_docs, patch_str, patch_entry.target.as_ref())?;
        }
    }

    for patch_str in &config.patches_strategic_merge {
        apply_patch_string(&mut rendered_docs, patch_str, None)?;
    }

    // 3. Apply Transformers: Namespace, NamePrefix/Suffix, Labels, Annotations
    for doc in &mut rendered_docs {
        apply_transformers(doc, &config);
    }

    // 3.5. Apply Kustomize v5+ Replacements
    apply_replacements(&mut rendered_docs, &config.replacements)?;

    // 4. Serialize into multi-document YAML
    let mut output = String::new();
    for doc in rendered_docs {
        if !output.is_empty() {
            output.push_str("---\n");
        }
        let serialized = serde_yaml::to_string(&doc)
            .map_err(|e| format!("Failed to serialize rendered YAML: {}", e))?;
        output.push_str(&serialized);
    }

    Ok(output)
}

fn apply_patch_string(
    docs: &mut [Value],
    patch_str: &str,
    target: Option<&PatchTarget>,
) -> Result<(), String> {
    let patch_doc: Value = serde_yaml::from_str(patch_str)
        .map_err(|e| format!("Failed to parse strategic patch: {}", e))?;

    let patch_kind = patch_doc.get("kind").and_then(|k| k.as_str());
    let patch_name = patch_doc
        .get("metadata")
        .and_then(|m| m.get("name"))
        .and_then(|n| n.as_str());

    for doc in docs.iter_mut() {
        let doc_kind = doc.get("kind").and_then(|k| k.as_str());
        let doc_name = doc
            .get("metadata")
            .and_then(|m| m.get("name"))
            .and_then(|n| n.as_str());

        let matches = match target {
            Some(t) => {
                let kind_match = t.kind.as_deref().map_or(true, |k| Some(k) == doc_kind);
                let name_match = t.name.as_deref().map_or(true, |n| Some(n) == doc_name);
                kind_match && name_match
            }
            None => {
                (patch_kind.is_none() || patch_kind == doc_kind)
                    && (patch_name.is_none() || patch_name == doc_name)
            }
        };

        if matches {
            merge_strategic(doc, &patch_doc);
        }
    }

    Ok(())
}

fn apply_transformers(doc: &mut Value, config: &KustomizationConfig) {
    let mapping = match doc {
        Value::Mapping(m) => m,
        _ => return,
    };

    let meta_key = Value::String("metadata".to_string());
    if !mapping.contains_key(&meta_key) {
        mapping.insert(meta_key.clone(), Value::Mapping(serde_yaml::Mapping::new()));
    }

    // First: transform metadata
    {
        let metadata = match mapping.get_mut(&meta_key) {
            Some(Value::Mapping(m)) => m,
            _ => return,
        };

        // 1. Namespace transformer
        if let Some(ref ns) = config.namespace {
            metadata.insert(
                Value::String("namespace".to_string()),
                Value::String(ns.clone()),
            );
        }

        // 2. NamePrefix / NameSuffix transformer
        if let Some(Value::String(ref orig_name)) = metadata.get(&Value::String("name".to_string()))
        {
            let mut new_name = orig_name.clone();
            if let Some(ref prefix) = config.name_prefix {
                new_name = format!("{}{}", prefix, new_name);
            }
            if let Some(ref suffix) = config.name_suffix {
                new_name = format!("{}{}", new_name, suffix);
            }
            metadata.insert(Value::String("name".to_string()), Value::String(new_name));
        }

        // 3. Common Labels in metadata
        if !config.common_labels.is_empty() {
            inject_key_values(metadata, "labels", &config.common_labels);
        }

        // 4. Common Annotations
        if !config.common_annotations.is_empty() {
            inject_key_values(metadata, "annotations", &config.common_annotations);
        }
    }

    // Second: inject pod template labels if workload
    if !config.common_labels.is_empty() {
        let spec_key = Value::String("spec".to_string());
        if let Some(Value::Mapping(spec)) = mapping.get_mut(&spec_key) {
            let tpl_key = Value::String("template".to_string());
            if let Some(Value::Mapping(template)) = spec.get_mut(&tpl_key) {
                if !template.contains_key(&meta_key) {
                    template.insert(meta_key.clone(), Value::Mapping(serde_yaml::Mapping::new()));
                }
                if let Some(Value::Mapping(tpl_meta)) = template.get_mut(&meta_key) {
                    inject_key_values(tpl_meta, "labels", &config.common_labels);
                }
            }
        }
    }
}

fn inject_key_values(
    parent: &mut serde_yaml::Mapping,
    field_name: &str,
    entries: &HashMap<String, String>,
) {
    let key = Value::String(field_name.to_string());
    if !parent.contains_key(&key) {
        parent.insert(key.clone(), Value::Mapping(serde_yaml::Mapping::new()));
    }

    if let Some(Value::Mapping(child_map)) = parent.get_mut(&key) {
        for (k, v) in entries {
            child_map.insert(Value::String(k.clone()), Value::String(v.clone()));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_render_base() {
        let kustomization = r#"
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
"#;
        let base_yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 1
"#;
        let rendered =
            render_kustomization(kustomization, &[("deployment.yaml", base_yaml)]).unwrap();
        assert!(rendered.contains("kind: Deployment"));
        assert!(rendered.contains("name: web"));
    }

    #[test]
    fn test_render_namespace_and_name_prefix() {
        let kustomization = r#"
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: prod
namePrefix: corp-
nameSuffix: -svc
commonLabels:
  env: production
resources:
  - service.yaml
"#;
        let base_yaml = r#"
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  ports:
    - port: 80
"#;
        let rendered = render_kustomization(kustomization, &[("service.yaml", base_yaml)]).unwrap();
        assert!(rendered.contains("namespace: prod"));
        assert!(rendered.contains("name: corp-api-svc"));
        assert!(rendered.contains("env: production"));
    }

    #[test]
    fn test_render_overlay_patches() {
        let kustomization = r#"
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
patches:
  - patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: web
      spec:
        replicas: 5
    target:
      kind: Deployment
      name: web
"#;
        let base_yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 1
"#;
        let rendered = render_kustomization(kustomization, &[("deploy.yaml", base_yaml)]).unwrap();
        assert!(rendered.contains("replicas: 5"));
    }

    #[test]
    fn test_kustomize_replacements_field_injection() {
        let kustomization = r#"
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - configmap.yaml
  - deployment.yaml
replacements:
  - source:
      kind: ConfigMap
      name: my-config
      fieldPath: data.CLUSTER_NAME
    targets:
      - select:
          kind: Deployment
          name: app
        fieldPaths:
          - spec.clusterTarget
"#;
        let cm_yaml = r#"
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  CLUSTER_NAME: prod-us-east-1
"#;
        let dep_yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 2
"#;
        let rendered = render_kustomization(
            kustomization,
            &[("configmap.yaml", cm_yaml), ("deployment.yaml", dep_yaml)],
        )
        .unwrap();

        assert!(rendered.contains("CLUSTER_NAME: prod-us-east-1"));
        assert!(rendered.contains("clusterTarget: prod-us-east-1"));
    }
}
