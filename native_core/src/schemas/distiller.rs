//! Pure Rust CustomResourceDefinition (CRD) Schema Distiller.
//!
//! Why: Ingests CRDs from files, directories, or cluster exports and distills their
//!      OpenAPI v3 schemas into lightweight NativeSchema representations. Ensures
//!      supported structural checks for custom resources without external dependencies.
//! Unsupported validation constraints are rejected rather than silently discarded.

use crate::models::{NativeSchema, SchemaProperty};
use serde::Deserialize;
use serde_yaml::Value;
use std::collections::HashSet;
use std::path::Path;

/// Distills CRD schemas from a raw YAML manifest string (supports multi-document streams).
pub fn distill_crd_content(content: &str) -> Result<Vec<NativeSchema>, String> {
    let mut schemas = Vec::new();

    for (index, document) in serde_yaml::Deserializer::from_str(content).enumerate() {
        let crd = Value::deserialize(document)
            .map_err(|error| format!("Invalid YAML in CRD document {}: {}", index + 1, error))?;
        if crd.is_null() {
            continue;
        }

        if crd["kind"].as_str() != Some("CustomResourceDefinition") {
            continue;
        }

        let spec = &crd["spec"];
        let group = spec["group"]
            .as_str()
            .filter(|value| !value.trim().is_empty())
            .ok_or_else(|| {
                format!(
                    "Invalid CRD document {}: spec.group must be a non-empty string",
                    index + 1
                )
            })?
            .to_string();
        let kind = spec["names"]["kind"]
            .as_str()
            .filter(|value| !value.trim().is_empty())
            .ok_or_else(|| {
                format!(
                    "Invalid CRD document {}: spec.names.kind must be a non-empty string",
                    index + 1
                )
            })?
            .to_string();

        // Check for v1beta1 top-level validation schema fallback
        let global_schema = spec
            .get("validation")
            .and_then(|v| v.get("openAPIV3Schema"))
            .and_then(|s| s.as_mapping());

        // 1. Multi-version CRDs (apiextensions.k8s.io/v1 and newer v1beta1)
        if let Some(versions) = spec["versions"].as_sequence() {
            if versions.is_empty() {
                return Err(format!(
                    "Invalid CRD document {}: spec.versions must not be empty",
                    index + 1
                ));
            }
            for v_info in versions {
                let version_name = v_info["name"]
                    .as_str()
                    .filter(|value| !value.trim().is_empty())
                    .ok_or_else(|| {
                        format!(
                            "Invalid CRD document {}: each spec.versions entry requires a non-empty name",
                            index + 1
                        )
                    })?;
                let api_version = if group.is_empty() {
                    version_name.to_string()
                } else {
                    format!("{}/{}", group, version_name)
                };

                let schema = v_info
                    .get("schema")
                    .and_then(|s| s.get("openAPIV3Schema"))
                    .and_then(|s| s.as_mapping())
                    .or(global_schema);

                if schema.is_none() {
                    return Err(format!(
                        "Invalid CRD document {}: version '{}' has no openAPIV3Schema",
                        index + 1,
                        version_name
                    ));
                }

                validate_supported_crd_schema(schema.unwrap(), "openAPIV3Schema", 0)?;
                let properties = extract_properties_from_openapi(schema);

                schemas.push(NativeSchema {
                    kind: kind.clone(),
                    api_version,
                    properties,
                });
            }
        } else if let Some(version_name) = spec["version"]
            .as_str()
            .filter(|value| !value.trim().is_empty())
        {
            // 2. Legacy single-version CRDs (apiextensions.k8s.io/v1beta1)
            let api_version = if group.is_empty() {
                version_name.to_string()
            } else {
                format!("{}/{}", group, version_name)
            };

            if global_schema.is_none() {
                return Err(format!(
                    "Invalid CRD document {}: spec.validation.openAPIV3Schema is required",
                    index + 1
                ));
            }
            validate_supported_crd_schema(global_schema.unwrap(), "openAPIV3Schema", 0)?;
            let properties = extract_properties_from_openapi(global_schema);

            schemas.push(NativeSchema {
                kind,
                api_version,
                properties,
            });
        } else {
            return Err(format!(
                "Invalid CRD document {}: expected a non-empty spec.versions array or spec.version",
                index + 1
            ));
        }
    }

    Ok(schemas)
}

/// The distilled representation cannot enforce arbitrary OpenAPI constraints.
/// Refuse schemas that would otherwise lose validation requirements on ingestion.
fn validate_supported_crd_schema(
    schema: &serde_yaml::Mapping,
    path: &str,
    depth: usize,
) -> Result<(), String> {
    if depth > 64 {
        return Err(format!(
            "CRD schema nesting exceeds supported depth at '{}'",
            path
        ));
    }
    if depth == 0
        && schema
            .get(Value::String("type".into()))
            .and_then(Value::as_str)
            != Some("object")
    {
        return Err("Unsupported CRD root schema: type must be object".into());
    }
    for (key, value) in schema {
        let key = key
            .as_str()
            .ok_or_else(|| format!("CRD schema key must be a string at '{}'", path))?;
        match key {
            "description" | "title" | "default" | "example" | "externalDocs" => {},
            "type" => {
                if !value.as_str().is_some_and(|kind| matches!(kind, "object" | "array" | "string" | "boolean" | "integer" | "number")) {
                    return Err(format!("Unsupported CRD type at '{}'", path));
                }
            },
            "nullable" if value.as_bool() == Some(false) => {},
            "additionalProperties" if value.as_bool() == Some(true) => {},
            "enum" => {
                if path == "openAPIV3Schema" || path.ends_with("/items") || schema.get(Value::String("type".into())).and_then(Value::as_str).is_some_and(|kind| kind != "string") || !value.as_sequence().is_some_and(|values| !values.is_empty() && values.iter().all(|value| value.as_str().is_some())) {
                    return Err(format!("Unsupported CRD enum at '{}': only string property enums are supported", path));
                }
            },
            "required" => {
                let properties = schema.get(Value::String("properties".into())).and_then(Value::as_mapping);
                let Some(required) = value.as_sequence() else {
                    return Err(format!("CRD required must be an array at '{}'", path));
                };
                for field in required {
                    if field.as_str().is_none() || !properties.is_some_and(|properties| properties.contains_key(field)) {
                        return Err(format!("CRD required field has no supported property definition at '{}'", path));
                    }
                }
            },
            "properties" => {
                let fields = value.as_mapping().ok_or_else(|| format!("CRD properties must be an object at '{}'", path))?;
                for (name, field) in fields {
                    let name = name.as_str().ok_or_else(|| format!("CRD property name must be a string at '{}'", path))?;
                    let field = field.as_mapping().ok_or_else(|| format!("CRD property schema must be an object at '{}/{}'", path, name))?;
                    validate_supported_crd_schema(field, &format!("{}/properties/{}", path, name), depth + 1)?;
                }
            },
            "items" => {
                let items = value.as_mapping().ok_or_else(|| format!("CRD items must be an object at '{}'", path))?;
                validate_supported_crd_schema(items, &format!("{}/items", path), depth + 1)?;
            },
            _ => return Err(format!("Unsupported CRD validation keyword '{}' at '{}'; this constraint cannot be silently omitted", key, path)),
        }
    }
    Ok(())
}

/// Helper function to extract SchemaProperties from an openAPIV3Schema mapping.
fn extract_properties_from_openapi(
    schema_mapping: Option<&serde_yaml::Mapping>,
) -> Vec<SchemaProperty> {
    let mut properties = Vec::new();
    let schema = match schema_mapping {
        Some(s) => s,
        None => return properties,
    };

    // Extract top-level required fields list
    let mut required_fields = HashSet::new();
    if let Some(req_seq) = schema
        .get(&Value::String("required".to_string()))
        .and_then(|r| r.as_sequence())
    {
        for item in req_seq {
            if let Some(field_name) = item.as_str() {
                required_fields.insert(field_name.to_string());
            }
        }
    }

    if let Some(props) = schema
        .get(&Value::String("properties".to_string()))
        .and_then(|p| p.as_mapping())
    {
        for (prop_key, prop_val) in props {
            if let Some(prop_name) = prop_key.as_str() {
                let is_required = required_fields.contains(prop_name)
                    || prop_val
                        .get(&Value::String("required".to_string()))
                        .and_then(|r| r.as_bool())
                        .unwrap_or(false);

                let mut enum_values = Vec::new();
                if let Some(enum_seq) = prop_val
                    .get(&Value::String("enum".to_string()))
                    .and_then(|e| e.as_sequence())
                {
                    for ev in enum_seq {
                        if let Some(s) = ev.as_str() {
                            enum_values.push(s.to_string());
                        }
                    }
                }

                properties.push(SchemaProperty {
                    name: prop_name.to_string(),
                    prop_type: prop_val
                        .get(&Value::String("type".to_string()))
                        .and_then(|t| t.as_str())
                        .unwrap_or_else(|| {
                            if prop_val.get("properties").is_some() {
                                "object"
                            } else if prop_val.get("items").is_some() {
                                "array"
                            } else if prop_val.get("enum").is_some() {
                                "string"
                            } else {
                                "any"
                            }
                        })
                        .to_string(),
                    required: is_required,
                    description: prop_val
                        .get(&Value::String("description".to_string()))
                        .and_then(|d| d.as_str())
                        .unwrap_or("")
                        .to_string(),
                    enum_values,
                });
            }
        }
    }

    if let Ok(definition) = serde_json::to_value(schema) {
        super::nested::append_openapi_properties(&definition, "", &mut properties);
    }

    properties
}

/// Distills CRD schemas from a manifest file on disk.
pub fn distill_crd_file(path: &str) -> Result<Vec<NativeSchema>, String> {
    let content = std::fs::read_to_string(path)
        .map_err(|error| format!("Failed to read CRD file '{}': {}", path, error))?;
    distill_crd_content(&content)
}

/// Recursively scans a directory for `.yaml` and `.yml` files, distilling all CRD schemas found.
pub fn distill_crd_directory(dir_path: &str) -> Result<Vec<NativeSchema>, String> {
    let mut collected = Vec::new();
    let mut seen_keys = HashSet::new();

    let path = Path::new(dir_path);
    if !path.is_dir() {
        return Err(format!(
            "CRD directory '{}' does not exist or is not a directory.",
            dir_path
        ));
    }

    fn visit_dir(
        dir: &Path,
        results: &mut Vec<NativeSchema>,
        seen: &mut HashSet<String>,
    ) -> Result<(), String> {
        let entries = std::fs::read_dir(dir).map_err(|error| {
            format!(
                "Failed to list CRD directory '{}': {}",
                dir.display(),
                error
            )
        })?;
        for entry in entries {
            let entry = entry.map_err(|error| {
                format!(
                    "Failed to read an entry in CRD directory '{}': {}",
                    dir.display(),
                    error
                )
            })?;
            let p = entry.path();
            let file_type = entry.file_type().map_err(|error| {
                format!("Failed to inspect CRD path '{}': {}", p.display(), error)
            })?;
            if file_type.is_dir() {
                visit_dir(&p, results, seen)?;
            } else if file_type.is_file() {
                if let Some(ext) = p.extension().and_then(|e| e.to_str()) {
                    if ext == "yaml" || ext == "yml" {
                        let content = std::fs::read_to_string(&p).map_err(|error| {
                            format!("Failed to read CRD file '{}': {}", p.display(), error)
                        })?;
                        let schemas = distill_crd_content(&content).map_err(|error| {
                            format!("Invalid CRD file '{}': {}", p.display(), error)
                        })?;
                        for schema in schemas {
                            let key = format!("{}/{}", schema.api_version, schema.kind);
                            if seen.insert(key) {
                                results.push(schema);
                            }
                        }
                    }
                }
            }
        }
        Ok(())
    }

    visit_dir(path, &mut collected, &mut seen_keys)?;
    Ok(collected)
}

/// Backward compatibility facade for native_extract_schema_from_crd.
pub fn native_extract_schema_from_crd(content: &str) -> Result<Vec<NativeSchema>, String> {
    distill_crd_content(content)
}

#[cfg(test)]
mod contract_tests {
    use super::*;

    #[test]
    fn unsupported_validation_constraints_cannot_be_silently_distilled() {
        for constraint in [
            "minimum: 1",
            "pattern: '^safe$'",
            "additionalProperties: false",
            "$ref: '#/definitions/Other'",
            "oneOf: []",
            "nullable: true",
            "x-kubernetes-validations: []",
            "enum: [1, 2]",
        ] {
            let schema: serde_yaml::Mapping = serde_yaml::from_str(&format!(
                "type: object\nproperties:\n  spec:\n    type: object\n    properties:\n      value:\n        type: string\n        {}\n", constraint
            )).unwrap();
            let error = validate_supported_crd_schema(&schema, "openAPIV3Schema", 0).unwrap_err();
            assert!(error.contains("Unsupported CRD"), "{constraint}: {error}");
        }
    }

    #[test]
    fn structural_schema_and_property_names_are_accepted() {
        let schema: serde_yaml::Mapping = serde_yaml::from_str(
            "type: object\nrequired: [spec]\nproperties:\n  spec:\n    type: object\n    properties:\n      minimum:\n        type: string\n        enum: [small, large]\n      values:\n        type: array\n        items:\n          type: integer\n"
        ).unwrap();
        validate_supported_crd_schema(&schema, "openAPIV3Schema", 0).unwrap();
    }
}
