//! Kubernetes CustomResourceDefinition (CRD) OpenAPI Extension Validator.
//!
//! Why: Validates CRD instance manifests against Kubernetes OpenAPI extensions:
//! `x-kubernetes-immutable`, `x-kubernetes-list-type` (`map`, `set`),
//! `x-kubernetes-list-map-keys`, and `x-kubernetes-preserve-unknown-fields`.
//! Prevents apiserver rejection on custom resources like CertManager, Istio, or ArgoCD.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

use crate::models::{SchemaViolation, SemanticManifest, SemanticNode};

/// Configuration rule for CRD instance validation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrdValidationRule {
    pub field_path: String,
    pub is_immutable: bool,
    pub list_type: Option<String>, // "map", "set", "atomic"
    pub list_map_keys: Vec<String>,
    pub preserve_unknown_fields: bool,
    pub allowed_fields: Vec<String>,
}

/// 3-tuple index key `(Group, Version, Kind)` preventing collisions across multiple versions in `.spec.versions[]`.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct CrdKey {
    pub group: String,
    pub version: String,
    pub kind: String,
}

impl CrdKey {
    pub fn new(
        group: impl Into<String>,
        version: impl Into<String>,
        kind: impl Into<String>,
    ) -> Self {
        Self {
            group: group.into(),
            version: version.into(),
            kind: kind.into(),
        }
    }

    pub fn from_api_version_and_kind(api_version: &str, kind: &str) -> Self {
        let (group, version) = match api_version.split_once('/') {
            Some((g, v)) => (g.to_string(), v.to_string()),
            None => (String::new(), api_version.to_string()),
        };
        Self {
            group,
            version,
            kind: kind.to_string(),
        }
    }
}

/// Multi-version CRD schema registry indexing rules strictly by `(Group, Version, Kind)`.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CrdSchemaRegistry {
    rules: std::collections::HashMap<CrdKey, Vec<CrdValidationRule>>,
}

impl CrdSchemaRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn register(&mut self, key: CrdKey, rules: Vec<CrdValidationRule>) {
        self.rules.entry(key).or_default().extend(rules);
    }

    pub fn get(&self, key: &CrdKey) -> Option<&[CrdValidationRule]> {
        self.rules.get(key).map(|v| v.as_slice())
    }

    pub fn get_for_manifest(&self, manifest: &SemanticManifest) -> Option<&[CrdValidationRule]> {
        let kind = manifest.root.find_value("kind")?;
        let api_version = manifest.root.find_value("apiVersion")?;
        let clean_kind = kind.trim_matches('"').trim_matches('\'');
        let clean_api_v = api_version.trim_matches('"').trim_matches('\'');
        let key = CrdKey::from_api_version_and_kind(clean_api_v, clean_kind);
        self.get(&key)
    }

    pub fn len(&self) -> usize {
        self.rules.len()
    }

    pub fn is_empty(&self) -> bool {
        self.rules.is_empty()
    }
}

/// Validates a single CRD instance against schema constraints.
///
/// Why: Detects duplicate list-map keys and unpreserved extra fields before admission.
pub fn validate_crd_instance(
    manifest: &SemanticManifest,
    rules: &[CrdValidationRule],
) -> Vec<SchemaViolation> {
    let mut violations = Vec::new();

    for rule in rules {
        // 1. Validate list-type constraints (map/set)
        if let Some(target_node) = manifest.root.find_node_by_path(&rule.field_path) {
            if let Some(ref lt) = rule.list_type {
                match lt.as_str() {
                    "set" => {
                        let mut seen = HashSet::new();
                        for child in &target_node.children {
                            if let Some(ref val) = child.value {
                                if !seen.insert(val.trim().to_string()) {
                                    let line_no =
                                        child.shards.first().map(|s| s.line_no).unwrap_or(0);
                                    violations.push(SchemaViolation {
                                        field_path: rule.field_path.clone(),
                                        message: format!(
                                            "CRD list-type 'set' violation: duplicate entry '{}' in '{}'",
                                            val.trim(), rule.field_path
                                        ),
                                        severity: "High".to_string(),
                                        suggested_value: val.trim().to_string(),
                                        line_no,
                                    });
                                    break;
                                }
                            }
                        }
                    }
                    "map" => {
                        if !rule.list_map_keys.is_empty() {
                            let mut seen_keys = HashSet::new();
                            for item in &target_node.children {
                                let mut composite_key = String::new();
                                for k in &rule.list_map_keys {
                                    if let Some(val_node) = item.find_node(k) {
                                        if let Some(ref v) = val_node.value {
                                            composite_key.push_str(v.trim());
                                            composite_key.push(':');
                                        }
                                    }
                                }
                                if !composite_key.is_empty() {
                                    if !seen_keys.insert(composite_key.clone()) {
                                        let line_no =
                                            item.shards.first().map(|s| s.line_no).unwrap_or(0);
                                        violations.push(SchemaViolation {
                                            field_path: rule.field_path.clone(),
                                            message: format!(
                                                "CRD list-type 'map' violation: duplicate composite key '{}' for keys {:?} in '{}'",
                                                composite_key.trim_end_matches(':'), rule.list_map_keys, rule.field_path
                                            ),
                                            severity: "High".to_string(),
                                            suggested_value: composite_key,
                                            line_no,
                                        });
                                        break;
                                    }
                                }
                            }
                        }
                    }
                    _ => {}
                }
            }

            // 2. Validate unknown fields when preserve-unknown-fields is false
            if !rule.preserve_unknown_fields && !rule.allowed_fields.is_empty() {
                for child in &target_node.children {
                    if !rule.allowed_fields.contains(&child.key) {
                        let line_no = child.shards.first().map(|s| s.line_no).unwrap_or(0);
                        violations.push(SchemaViolation {
                            field_path: format!("{}.{}", rule.field_path, child.key),
                            message: format!(
                                "CRD schema violation: unrecognized field '{}' not permitted when x-kubernetes-preserve-unknown-fields is false",
                                child.key
                            ),
                            severity: "Medium".to_string(),
                            suggested_value: String::new(),
                            line_no,
                        });
                    }
                }
            }
        }
    }

    violations
}

/// Validates that immutable fields are not mutated between two revisions.
///
/// Why: Kubernetes API server rejects updates that attempt to modify `x-kubernetes-immutable` fields.
pub fn validate_crd_immutability(
    old_manifest: &SemanticManifest,
    new_manifest: &SemanticManifest,
    immutable_paths: &[&str],
) -> Vec<SchemaViolation> {
    let mut violations = Vec::new();

    for path in immutable_paths {
        let old_val = old_manifest
            .root
            .find_node_by_path(path)
            .and_then(|n| n.value.as_deref());
        let new_node = new_manifest.root.find_node_by_path(path);
        let new_val = new_node.as_ref().and_then(|n| n.value.as_deref());

        if let (Some(old), Some(new)) = (old_val, new_val) {
            if old.trim() != new.trim() {
                let line_no = new_node
                    .and_then(|n| n.shards.first().map(|s| s.line_no))
                    .unwrap_or(0);
                violations.push(SchemaViolation {
                    field_path: path.to_string(),
                    message: format!(
                        "CRD immutability violation: field '{}' is immutable (x-kubernetes-immutable: true). Changed from '{}' to '{}'",
                        path, old.trim(), new.trim()
                    ),
                    severity: "Critical".to_string(),
                    suggested_value: old.trim().to_string(),
                    line_no,
                });
            }
        }
    }

    violations
}

impl SemanticNode {
    /// Traverses a dot-delimited path (e.g. `spec.template.spec`) to find a descendant node.
    pub fn find_node_by_path(&self, path: &str) -> Option<&SemanticNode> {
        let trimmed = path.trim().trim_start_matches('.');
        if trimmed.is_empty() {
            return Some(self);
        }
        let segments: Vec<&str> = trimmed.split('.').collect();
        let mut current = self;
        let mut direct_match = true;

        for seg in &segments {
            if *seg == "spec" && current.key == "spec" {
                continue;
            }
            if let Some(child) = current.children.iter().find(|c| c.key == *seg) {
                current = child;
            } else if current.key == *seg {
                // Already at matching node
            } else {
                direct_match = false;
                break;
            }
        }

        if direct_match {
            Some(current)
        } else {
            // Fallback: search recursively for the first segment
            if segments.len() == 1 {
                self.find_node_recursive(segments[0])
            } else if let Some(first_node) = self.find_node_recursive(segments[0]) {
                let remaining = segments[1..].join(".");
                first_node.find_node_by_path(&remaining)
            } else {
                None
            }
        }
    }

    /// Recursively searches descendant nodes for a matching key.
    pub fn find_node_recursive(&self, key: &str) -> Option<&SemanticNode> {
        if self.key == key {
            return Some(self);
        }
        for child in &self.children {
            if let Some(found) = child.find_node_recursive(key) {
                return Some(found);
            }
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_list_map_keys_unique() {
        let yaml = r#"
apiVersion: apps/v1
kind: Deployment
spec:
  containers:
    - name: web
      image: nginx:1.25
    - name: web
      image: redis:7
"#;
        let manifest = native_structurize(native_shard(yaml));
        let rules = vec![CrdValidationRule {
            field_path: "containers".to_string(),
            is_immutable: false,
            list_type: Some("map".to_string()),
            list_map_keys: vec!["name".to_string()],
            preserve_unknown_fields: true,
            allowed_fields: vec![],
        }];

        let violations = validate_crd_instance(&manifest, &rules);
        assert_eq!(violations.len(), 1);
        assert!(violations[0]
            .message
            .contains("duplicate composite key 'web'"));
    }

    #[test]
    fn test_preserve_unknown_fields_rejection() {
        let yaml = r#"
apiVersion: example.com/v1
kind: Database
spec:
  engine: postgres
  unknownSetting: true
"#;
        let manifest = native_structurize(native_shard(yaml));
        let rules = vec![CrdValidationRule {
            field_path: "spec".to_string(),
            is_immutable: false,
            list_type: None,
            list_map_keys: vec![],
            preserve_unknown_fields: false,
            allowed_fields: vec!["engine".to_string(), "storage".to_string()],
        }];

        let violations = validate_crd_instance(&manifest, &rules);
        assert_eq!(violations.len(), 1);
        assert!(violations[0]
            .message
            .contains("unrecognized field 'unknownSetting'"));
    }

    #[test]
    fn test_immutable_field_change() {
        let old_yaml = "apiVersion: v1\nkind: Service\nspec:\n  clusterIP: 10.96.0.1\n";
        let new_yaml = "apiVersion: v1\nkind: Service\nspec:\n  clusterIP: 10.96.0.50\n";

        let old_m = native_structurize(native_shard(old_yaml));
        let new_m = native_structurize(native_shard(new_yaml));

        let violations = validate_crd_immutability(&old_m, &new_m, &["clusterIP"]);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("CRD immutability violation"));
    }

    #[test]
    fn test_crd_multi_version_registry_no_collision() {
        let mut registry = CrdSchemaRegistry::new();

        let key_v1alpha1 = CrdKey::new("example.com", "v1alpha1", "Widget");
        let key_v1 = CrdKey::new("example.com", "v1", "Widget");

        let rule_alpha = CrdValidationRule {
            field_path: "spec.alphaField".to_string(),
            is_immutable: false,
            list_type: None,
            list_map_keys: vec![],
            preserve_unknown_fields: true,
            allowed_fields: vec![],
        };
        let rule_stable = CrdValidationRule {
            field_path: "spec.stableField".to_string(),
            is_immutable: true,
            list_type: None,
            list_map_keys: vec![],
            preserve_unknown_fields: false,
            allowed_fields: vec!["stableField".to_string()],
        };

        registry.register(key_v1alpha1.clone(), vec![rule_alpha]);
        registry.register(key_v1.clone(), vec![rule_stable]);

        assert_eq!(registry.len(), 2);

        let manifest_alpha = native_structurize(native_shard(
            "apiVersion: example.com/v1alpha1\nkind: Widget\nspec:\n  alphaField: true\n",
        ));
        let manifest_stable = native_structurize(native_shard(
            "apiVersion: example.com/v1\nkind: Widget\nspec:\n  stableField: val\n",
        ));

        let rules_alpha = registry
            .get_for_manifest(&manifest_alpha)
            .expect("rules for alpha");
        assert_eq!(rules_alpha[0].field_path, "spec.alphaField");

        let rules_stable = registry
            .get_for_manifest(&manifest_stable)
            .expect("rules for stable");
        assert_eq!(rules_stable[0].field_path, "spec.stableField");
    }
}
