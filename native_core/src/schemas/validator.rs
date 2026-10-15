//! Deep AST Schema Validator.
//!
//! Why: Validates SemanticManifest AST representations directly against OpenAPI v3
//!      schema definitions. Nested checks also validate reconstructed YAML values;
//!      distilled definitions do not retain every OpenAPI constraint.

use crate::models::{NativeSchema, SchemaViolation, SemanticManifest};

/// Validates a manifest directly against OpenAPI v3 schema definitions.
pub fn native_validate_ast_against_schema(
    manifest: &SemanticManifest,
    schemas: &[NativeSchema],
) -> Vec<SchemaViolation> {
    let mut violations = Vec::new();

    let doc_kind = manifest.root.find_value("kind");
    let doc_api_version = manifest.root.find_value("apiVersion");

    let kind_str = match &doc_kind {
        Some(k) => k.trim_matches('"').trim_matches('\''),
        None => return violations,
    };

    // Find schema matching kind (prefer matching apiVersion if available)
    let mut matching_schema = None;
    if let Some(ref api_v) = doc_api_version {
        let clean_api_v = api_v.trim_matches('"').trim_matches('\'');
        matching_schema = schemas.iter().find(|s| {
            s.kind.eq_ignore_ascii_case(kind_str) && !s.api_version.is_empty() && s.api_version.eq_ignore_ascii_case(clean_api_v)
        });
    }
    if matching_schema.is_none() {
        matching_schema = schemas.iter().find(|s| s.kind.eq_ignore_ascii_case(kind_str));
    }

    let schema = match matching_schema {
        Some(s) => s,
        None => return violations,
    };

    // Flag casing mismatch on kind (e.g. 'ingress' vs 'Ingress')
    if schema.kind != kind_str {
        violations.push(SchemaViolation {
            field_path: "kind".to_string(),
            message: format!(
                "Invalid Kind casing '{}', standard Kubernetes resource Kind is '{}'",
                kind_str, schema.kind
            ),
            severity: "High".to_string(),
            suggested_value: schema.kind.clone(),
            line_no: manifest
                .root
                .find_node("kind")
                .and_then(|node| node.shards.first().map(|shard| shard.line_no))
                .filter(|line| *line > 0)
                .unwrap_or(1),
        });
    }

    for prop in &schema.properties {
        if prop.name.starts_with('/') {
            continue;
        }
        let child_node = manifest.root.find_node(&prop.name);

        // 1. Required field validation
        if prop.required && child_node.is_none() {
            violations.push(SchemaViolation {
                field_path: prop.name.clone(),
                message: format!(
                    "Missing required field '{}' for Kind '{}'",
                    prop.name, schema.kind
                ),
                severity: "High".to_string(),
                suggested_value: default_value_for_type(&prop.prop_type),
                line_no: manifest
                    .root
                    .find_node("kind")
                    .and_then(|node| node.shards.first().map(|shard| shard.line_no))
                    .filter(|line| *line > 0)
                    .unwrap_or(1),
            });
            continue;
        }

        // 2. Type and Enum validation when field is present
        if let Some(node) = child_node {
            let node_line = node.shards.first().map(|s| s.line_no).unwrap_or(1);

            if let Some(ref val_raw) = node.value {
                let trimmed = val_raw.trim();
                let unquoted = trimmed.trim_matches('"').trim_matches('\'');

                let is_null_val = trimmed == "null" || trimmed == "~";
                let allows_null = !prop.required || prop.prop_type.contains("null");
                if is_null_val && allows_null {
                    // Valid optional/nullable field explicitly set to null
                } else if !validate_type_union(&prop.prop_type, trimmed, !node.children.is_empty())
                {
                    violations.push(SchemaViolation {
                        field_path: prop.name.clone(),
                        message: format!(
                            "Type mismatch: field '{}' expects type '{}', got '{}'",
                            prop.name, prop.prop_type, trimmed
                        ),
                        severity: "Medium".to_string(),
                        suggested_value: default_value_for_type(&prop.prop_type),
                        line_no: node_line,
                    });
                }

                // 3. Enum value validation
                if !prop.enum_values.is_empty() {
                    if !prop.enum_values.iter().any(|ev| ev == unquoted) {
                        violations.push(SchemaViolation {
                            field_path: prop.name.clone(),
                            message: format!(
                                "Invalid value '{}' for field '{}'. Allowed values: {:?}",
                                unquoted, prop.name, prop.enum_values
                            ),
                            severity: "Medium".to_string(),
                            suggested_value: prop
                                .enum_values
                                .first()
                                .cloned()
                                .unwrap_or_else(|| default_value_for_type(&prop.prop_type)),
                            line_no: node_line,
                        });
                    }
                }
            } else {
                let is_sequence = !node.children.is_empty()
                    && (node.children.iter().any(|child| {
                        child.shards.first().is_some_and(|shard| {
                            shard.is_list_item
                                || (shard.key.is_empty()
                                    && !shard.comment.is_empty()
                                    && child.children.iter().any(|gc| {
                                        gc.shards.first().is_some_and(|s| s.is_list_item)
                                    }))
                        })
                    }) || node.shards.iter().any(|shard| shard.is_list_item));
                let inferred = if node.children.is_empty() {
                    "null"
                } else if is_sequence {
                    "array"
                } else {
                    "object"
                };
                let kinds = serde_json::from_str::<Vec<String>>(&prop.prop_type)
                    .unwrap_or_else(|_| vec![prop.prop_type.clone()]);
                if !kinds.iter().any(|kind| kind == inferred) {
                    if inferred == "null" && (!prop.required || kinds.iter().any(|k| k == "null")) {
                        // Optional empty field, valid in K8s manifests
                    } else {
                        violations.push(SchemaViolation {
                            field_path: prop.name.clone(),
                            message: format!(
                                "Type mismatch: field '{}' expects '{}', got '{}'",
                                prop.name, prop.prop_type, inferred
                            ),
                            severity: "High".into(),
                            suggested_value: String::new(),
                            line_no: node_line,
                        });
                    }
                }
            }
        }
    }

    violations.extend(super::nested::validate_nested_properties(manifest, schema));

    // 4. OpenAPI structural and numeric constraints validation
    violations
        .extend(crate::schemas::constraints::validate_k8s_builtin_constraints(&manifest.root));

    // 5. Kubernetes CEL validation rules (x-kubernetes-validations)
    violations.extend(crate::cel::validate_builtin_cel_workloads(manifest));

    violations
}

/// Validates whether a value matches a single type or OpenAPI v3.1 structural type union (e.g. `["string", "null"]`).
pub fn validate_type_union(prop_type: &str, trimmed_val: &str, has_children: bool) -> bool {
    let clean_prop = prop_type.trim();

    // Check for JSON Schema Draft 2020-12 / OpenAPI v3.1 array representation or comma-separated union
    if clean_prop.starts_with('[') && clean_prop.ends_with(']') {
        let inner = &clean_prop[1..clean_prop.len() - 1];
        let parts: Vec<&str> = inner
            .split(',')
            .map(|s| s.trim().trim_matches('"').trim_matches('\''))
            .collect();
        return parts
            .iter()
            .any(|t| check_single_type(t, trimmed_val, has_children));
    }

    if clean_prop.contains(',') {
        let parts: Vec<&str> = clean_prop
            .split(',')
            .map(|s| s.trim().trim_matches('"').trim_matches('\''))
            .collect();
        return parts
            .iter()
            .any(|t| check_single_type(t, trimmed_val, has_children));
    }

    check_single_type(clean_prop, trimmed_val, has_children)
}

fn check_single_type(prop_type: &str, trimmed: &str, has_children: bool) -> bool {
    if has_children && trimmed.is_empty() {
        return matches!(prop_type, "object" | "array");
    }
    let Ok(value) = serde_yaml::from_str::<serde_yaml::Value>(trimmed) else {
        return false;
    };
    match prop_type {
        "null" => value.is_null(),
        "integer" => value.as_i64().is_some() || value.as_u64().is_some(),
        "number" => value.is_number(),
        "boolean" => value.is_bool(),
        "array" => value.is_sequence(),
        "object" => value.is_mapping(),
        "string" => value.is_string(),
        _ => true,
    }
}

#[cfg(test)]
mod type_tests {
    use super::*;
    #[test]
    fn types_do_not_accept_scalar_collection_values_or_quoted_primitives() {
        for kind in ["object", "array"] {
            for value in ["text", "1", "true", "null", "\"text\""] {
                assert!(!validate_type_union(kind, value, false), "{kind}: {value}");
            }
        }
        assert!(!validate_type_union("boolean", "\"true\"", false));
        assert!(!validate_type_union("integer", "1.5", false));
        assert!(validate_type_union("number", "1.5", false));
        assert!(validate_type_union("array", "[1, 2]", false));
        assert!(validate_type_union("object", "{name: app}", false));
        assert!(validate_type_union("[\"string\", \"null\"]", "null", false));
    }

    #[test]
    fn test_service_spec_is_object() {
        let yaml = r#"apiVersion: v1
kind: Service
metadata:
  labels:
    app.kubernetes.io/component: controller
    app.kubernetes.io/instance: ingress-nginx
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
    app.kubernetes.io/version: 1.15.1
  name: ingress-nginx-controller
  namespace: ingress-nginx
spec:
  ipFamilies:
  - IPv4
  ipFamilyPolicy: SingleStack
  ports:
  - appProtocol: http
    name: http
    port: 80
    protocol: TCP
    targetPort: http
  - appProtocol: https
    name: https
    port: 443
    protocol: TCP
    targetPort: https
  selector:
    app.kubernetes.io/component: controller
    app.kubernetes.io/instance: ingress-nginx
    app.kubernetes.io/name: ingress-nginx
  type: NodePort
"#;
        let shards = crate::sharder::native_shard(yaml);
        let manifest = crate::structurer::native_structurize(shards);
        let schemas = crate::schemas::native_get_schema_for_version("1.30");
        let violations = native_validate_ast_against_schema(&manifest, &schemas);
        assert!(
            violations.is_empty(),
            "Expected no violations, got {:?}",
            violations
        );
    }
}

/// Computes deterministic default fix value based on schema property type.
pub fn default_value_for_type(prop_type: &str) -> String {
    match prop_type {
        "boolean" => "true".to_string(),
        "integer" | "number" => "1".to_string(),
        "array" => "[]".to_string(),
        "object" => "{}".to_string(),
        _ => "\"yamlr-auto-fix\"".to_string(),
    }
}

/// Loads raw schema content from a filesystem path.
pub fn load_schema_from_path(path: &str) -> Option<String> {
    std::fs::read_to_string(path).ok()
}
