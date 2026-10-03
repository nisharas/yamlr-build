//! Ingestion and Validation Engine for Helm `values.schema.json`.
//!
//! Why: Helm charts commonly supply a `values.schema.json` according to the JSON Schema
//! specification. Validating user values directly against this schema catches type mismatches,
//! missing required fields, and invalid constraints before Helm rendering begins, eliminating
//! runtime template failures.

use crate::parsers::helm::values::update_shard_raw_line;
use crate::sharder::{native_reconstruct_yaml, native_shard};
use serde_json::Value as JsonValue;

/// Represents a violation of the Helm chart's `values.schema.json`.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct HelmSchemaViolation {
    pub path: String,
    pub message: String,
    pub expected_type: Option<String>,
}

/// Parses the raw JSON content of `values.schema.json`.
pub fn parse_helm_values_schema(schema_json: &str) -> Result<JsonValue, String> {
    serde_json::from_str(schema_json).map_err(|e| format!("Invalid Helm values.schema.json: {}", e))
}

/// Validates a raw values.yaml string against a Helm chart's `values.schema.json`.
pub fn validate_helm_values_against_schema(
    values_content: &str,
    schema_json: &str,
) -> Result<Vec<HelmSchemaViolation>, String> {
    let schema = parse_helm_values_schema(schema_json)?;
    let parsed_yaml: serde_yaml::Value = serde_yaml::from_str(values_content)
        .map_err(|e| format!("Invalid YAML in values content: {}", e))?;

    let mut violations = Vec::new();
    validate_node_recursive(&parsed_yaml, &schema, "", &mut violations);
    Ok(violations)
}

fn validate_node_recursive(
    val: &serde_yaml::Value,
    schema: &JsonValue,
    current_path: &str,
    violations: &mut Vec<HelmSchemaViolation>,
) {
    // 1. Check type constraint
    if let Some(expected_type) = schema.get("type").and_then(|t| t.as_str()) {
        let is_valid = match expected_type {
            "object" => val.is_mapping(),
            "array" => val.is_sequence(),
            "string" => val.is_string(),
            "integer" => val.is_i64() || val.is_u64(),
            "number" => val.is_number(),
            "boolean" => val.is_bool(),
            _ => true,
        };

        if !is_valid && !val.is_null() {
            let field = if current_path.is_empty() {
                "root"
            } else {
                current_path
            };
            violations.push(HelmSchemaViolation {
                path: field.to_string(),
                message: format!(
                    "Field '{}' expected type '{}', got incompatible YAML type",
                    field, expected_type
                ),
                expected_type: Some(expected_type.to_string()),
            });
        }
    }

    // 2. Check required properties if object
    if let (Some(mapping), Some(required)) = (
        val.as_mapping(),
        schema.get("required").and_then(|r| r.as_array()),
    ) {
        for req in required {
            if let Some(req_str) = req.as_str() {
                let key_val = serde_yaml::Value::String(req_str.to_string());
                if !mapping.contains_key(&key_val) {
                    let field = if current_path.is_empty() {
                        req_str.to_string()
                    } else {
                        format!("{}.{}", current_path, req_str)
                    };
                    violations.push(HelmSchemaViolation {
                        path: field.clone(),
                        message: format!(
                            "Missing required property '{}' according to values.schema.json",
                            field
                        ),
                        expected_type: None,
                    });
                }
            }
        }
    }

    // 3. Recurse into properties
    if let (Some(mapping), Some(properties)) = (
        val.as_mapping(),
        schema.get("properties").and_then(|p| p.as_object()),
    ) {
        for (prop_key, prop_schema) in properties {
            let key_val = serde_yaml::Value::String(prop_key.clone());
            if let Some(child_val) = mapping.get(&key_val) {
                let child_path = if current_path.is_empty() {
                    prop_key.clone()
                } else {
                    format!("{}.{}", current_path, prop_key)
                };
                validate_node_recursive(child_val, prop_schema, &child_path, violations);
            }
        }
    }
}

/// Heals a raw `values.yaml` string against a Helm chart's `values.schema.json` with 100% comment preservation.
pub fn heal_helm_values_against_schema(
    values_content: &str,
    schema_json: &str,
) -> Result<(String, Vec<String>), String> {
    let schema = parse_helm_values_schema(schema_json)?;
    let mut shards = native_shard(values_content);
    if shards.is_empty() {
        return Ok((values_content.to_string(), Vec::new()));
    }

    let mut changes = Vec::new();
    let mut modified = false;

    // Check schema properties at top and nested levels
    if let Some(properties) = schema.get("properties").and_then(|p| p.as_object()) {
        for i in 0..shards.len() {
            let key = shards[i].key.clone();
            let val_opt = shards[i].value.clone();

            if let Some(prop_schema) = properties.get(&key) {
                if let Some(expected_type) = prop_schema.get("type").and_then(|t| t.as_str()) {
                    if let Some(val) = val_opt {
                        let trimmed = val.trim();

                        // Auto-coercion 1: Quoted string to integer (e.g. "3" -> 3)
                        if expected_type == "integer"
                            && (trimmed.starts_with('"') || trimmed.starts_with('\''))
                        {
                            let unquoted = trimmed.trim_matches(|c| c == '"' || c == '\'');
                            if unquoted.parse::<i64>().is_ok() {
                                shards[i].value = Some(unquoted.to_string());
                                update_shard_raw_line(&mut shards[i], &key, unquoted);
                                changes.push(format!("Coerced quoted string '{}' to integer {} for field '{}' per schema", trimmed, unquoted, key));
                                modified = true;
                            }
                        }

                        // Auto-coercion 2: Unquoted number to string (e.g. 1.25 -> "1.25")
                        if expected_type == "string"
                            && !trimmed.starts_with('"')
                            && !trimmed.starts_with('\'')
                        {
                            if trimmed.parse::<f64>().is_ok() {
                                let quoted = format!("\"{}\"", trimmed);
                                shards[i].value = Some(quoted.clone());
                                update_shard_raw_line(&mut shards[i], &key, &quoted);
                                changes.push(format!("Coerced unquoted numeric literal {} to string {} for field '{}' per schema", trimmed, quoted, key));
                                modified = true;
                            }
                        }

                        // Auto-coercion 3: Quoted string to boolean (e.g. "true" -> true)
                        if expected_type == "boolean"
                            && (trimmed.starts_with('"') || trimmed.starts_with('\''))
                        {
                            let unquoted = trimmed
                                .trim_matches(|c| c == '"' || c == '\'')
                                .to_lowercase();
                            if unquoted == "true" || unquoted == "false" {
                                shards[i].value = Some(unquoted.clone());
                                update_shard_raw_line(&mut shards[i], &key, &unquoted);
                                changes.push(format!(
                                    "Coerced quoted string to boolean {} for field '{}' per schema",
                                    unquoted, key
                                ));
                                modified = true;
                            }
                        }
                    }
                }
            }
        }
    }

    if modified {
        Ok((native_reconstruct_yaml(&shards), changes))
    } else {
        Ok((values_content.to_string(), changes))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_helm_schema_type_mismatch() {
        let schema = r#"{
            "type": "object",
            "properties": {
                "replicaCount": { "type": "integer" },
                "imageTag": { "type": "string" }
            },
            "required": ["replicaCount"]
        }"#;

        let valid_values = "replicaCount: 3\nimageTag: \"v1.0\"\n";
        let violations = validate_helm_values_against_schema(valid_values, schema).unwrap();
        assert!(violations.is_empty());

        let invalid_values = "replicaCount: \"three\"\n";
        let violations = validate_helm_values_against_schema(invalid_values, schema).unwrap();
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].path, "replicaCount");
        assert_eq!(violations[0].expected_type, Some("integer".to_string()));
    }

    #[test]
    fn test_heal_helm_schema_type_coercion() {
        let schema = r#"{
            "type": "object",
            "properties": {
                "replicaCount": { "type": "integer" },
                "imageTag": { "type": "string" },
                "enabled": { "type": "boolean" }
            }
        }"#;

        let raw_values =
            "# Deployment configuration\nreplicaCount: \"5\"\nimageTag: 1.25\nenabled: \"true\"\n";
        let (healed, changes) = heal_helm_values_against_schema(raw_values, schema).unwrap();

        assert!(healed.contains("replicaCount: 5"));
        assert!(healed.contains("imageTag: \"1.25\""));
        assert!(healed.contains("enabled: true"));
        assert!(healed.contains("# Deployment configuration"));
        assert_eq!(changes.len(), 3);
    }
}
