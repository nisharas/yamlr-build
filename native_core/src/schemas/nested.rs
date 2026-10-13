//! Nested type checks using references retained in the distilled schema bundle.
//! Paths use JSON Pointer escaping; `*` represents an array element.

use crate::models::{
    NativeSchema, NativeShard, SchemaProperty, SchemaViolation, SemanticManifest, SemanticNode,
};
use serde_json::Value;
use std::collections::HashMap;

pub(super) fn append_nested_properties(
    definition: &Value,
    definitions: &HashMap<String, Value>,
    output: &mut Vec<SchemaProperty>,
) {
    // Internal definitions are used through resource references, not as resources.
    if definition.get("kind").is_none() {
        return;
    }
    expand(definition, definitions, "", &mut Vec::new(), output);
}

/// Retain nested CRD properties using the same escaped path contract.
pub(super) fn append_openapi_properties(
    definition: &Value,
    prefix: &str,
    output: &mut Vec<SchemaProperty>,
) {
    let Some(fields) = definition.get("properties").and_then(Value::as_object) else {
        return;
    };
    let required = definition.get("required").and_then(Value::as_array);
    for (name, field) in fields {
        let path = format!("{prefix}/{}", escape(name));
        let mut kind = field
            .get("type")
            .map(|kind| {
                kind.as_str()
                    .map(str::to_owned)
                    .unwrap_or_else(|| kind.to_string())
            })
            .unwrap_or_else(|| {
                if field.get("properties").is_some() {
                    "object".into()
                } else {
                    "any".into()
                }
            });
        if field.get("nullable").and_then(Value::as_bool) == Some(true) && !kind.starts_with('[') {
            kind = serde_json::json!([kind, "null"]).to_string();
        }
        if !prefix.is_empty() {
            output.push(SchemaProperty {
                name: path.clone(),
                prop_type: kind,
                required: required
                    .is_some_and(|names| names.iter().any(|key| key.as_str() == Some(name))),
                description: String::new(),
                enum_values: field
                    .get("enum")
                    .and_then(Value::as_array)
                    .map(|values| {
                        values
                            .iter()
                            .filter_map(Value::as_str)
                            .map(str::to_owned)
                            .collect()
                    })
                    .unwrap_or_default(),
            });
        }
        append_openapi_properties(field, &path, output);
        if let Some(items) = field.get("items") {
            let item_path = format!("{path}/*");
            output.push(SchemaProperty {
                name: item_path.clone(),
                prop_type: items
                    .get("type")
                    .and_then(Value::as_str)
                    .unwrap_or("any")
                    .into(),
                required: false,
                description: String::new(),
                enum_values: Vec::new(),
            });
            append_openapi_properties(items, &item_path, output);
        }
    }
}

fn escape(key: &str) -> String {
    key.replace('~', "~0").replace('/', "~1")
}
fn decode(key: &str) -> String {
    key.replace("~1", "/").replace("~0", "~")
}

fn expand(
    definition: &Value,
    definitions: &HashMap<String, Value>,
    prefix: &str,
    active: &mut Vec<String>,
    output: &mut Vec<SchemaProperty>,
) {
    let Some(fields) = definition.get("fields").and_then(Value::as_object) else {
        return;
    };
    for (name, field) in fields {
        let path = format!("{prefix}/{}", escape(name));
        let kind = field
            .get("type")
            .and_then(Value::as_str)
            .unwrap_or_else(|| match field.get("ref").and_then(Value::as_str) {
                Some("IntOrString") => "int-or-string",
                Some("Time" | "MicroTime") => "timestamp",
                Some("Quantity" | "Duration") => "string",
                Some(reference) if definitions.contains_key(reference) => "object",
                Some(_) => "unresolved-reference",
                None => "string",
            });
        if !prefix.is_empty() {
            output.push(SchemaProperty {
                name: path.clone(),
                prop_type: kind.to_owned(),
                required: field
                    .get("required")
                    .and_then(Value::as_bool)
                    .unwrap_or(false),
                description: String::new(),
                enum_values: field
                    .get("enum")
                    .and_then(Value::as_array)
                    .map(|values| {
                        values
                            .iter()
                            .filter_map(Value::as_str)
                            .map(str::to_owned)
                            .collect()
                    })
                    .unwrap_or_default(),
            });
        }
        let child_prefix = if kind == "array" {
            let item_path = format!("{path}/*");
            if let Some(item_type) = field.get("item_type").and_then(Value::as_str) {
                output.push(SchemaProperty {
                    name: item_path.clone(),
                    prop_type: item_type.to_owned(),
                    required: false,
                    description: String::new(),
                    enum_values: Vec::new(),
                });
            }
            item_path
        } else {
            path
        };
        if let Some(reference) = field.get("ref").and_then(Value::as_str) {
            // Recursive definitions cannot be fully expanded into finite flat paths.
            // Stop cycles; no universal schema-validation claim is made.
            if active.iter().any(|entry| entry == reference) {
                continue;
            }
            if let Some(nested) = definitions.get(reference) {
                active.push(reference.to_owned());
                expand(nested, definitions, &child_prefix, active, output);
                active.pop();
            }
        } else if field.get("fields").is_some() {
            expand(field, definitions, &child_prefix, active, output);
        }
    }
}

pub(super) fn validate_nested_properties(
    manifest: &SemanticManifest,
    schema: &NativeSchema,
) -> Vec<SchemaViolation> {
    if !schema
        .properties
        .iter()
        .any(|property| property.name.starts_with('/'))
    {
        return Vec::new();
    }
    let mut shards = Vec::new();
    fn collect<'a>(node: &'a SemanticNode, shards: &mut Vec<&'a NativeShard>) {
        shards.extend(node.shards.iter());
        for child in &node.children {
            collect(child, shards);
        }
    }
    collect(&manifest.root, &mut shards);
    shards.sort_by_key(|shard| shard.line_no);
    shards.dedup_by_key(|shard| shard.line_no);
    let source = shards
        .iter()
        .map(|shard| {
            if shard.key == "value" {
                if let Some(val) = &shard.value {
                    if (val.starts_with('"') && val.ends_with('"')) || (val.starts_with('\'') && val.ends_with('\'')) {
                        let indent = " ".repeat(shard.indent);
                        return format!("{indent}value: {val}");
                    }
                }
            }
            shard.raw_line.clone()
        })
        .collect::<Vec<_>>()
        .join("\n");
    let value: serde_yaml::Value = match serde_yaml::from_str(&source) {
        Ok(value) => value,
        Err(_) => return Vec::new(),
    };
    let mut violations = Vec::new();
    for property in schema
        .properties
        .iter()
        .filter(|property| property.name.starts_with('/'))
    {
        let segments = property.name[1..]
            .split('/')
            .map(decode)
            .collect::<Vec<_>>();
        visit(
            &value,
            &segments,
            "",
            property,
            &manifest.root,
            &mut violations,
        );
    }
    violations
}

fn visit(
    value: &serde_yaml::Value,
    segments: &[String],
    path: &str,
    property: &SchemaProperty,
    root: &SemanticNode,
    violations: &mut Vec<SchemaViolation>,
) {
    if segments.is_empty() {
        if !property.required && value.is_null() {
            return;
        }
        let is_tolerated_bool_string = property.prop_type == "string" && value.is_bool();
        if !matches_type(value, &property.prop_type) && !is_tolerated_bool_string {
            violations.push(SchemaViolation {
                field_path: path.into(),
                message: format!(
                    "Type mismatch: field '{path}' expects '{}'",
                    property.prop_type
                ),
                severity: "High".into(),
                suggested_value: String::new(),
                line_no: source_line(root, path),
            });
        } else if !property.enum_values.is_empty()
            && value
                .as_str()
                .is_some_and(|value| !property.enum_values.iter().any(|allowed| allowed == value))
        {
            violations.push(SchemaViolation {
                field_path: path.into(),
                message: format!("Invalid enum value at '{path}'"),
                severity: "High".into(),
                suggested_value: String::new(),
                line_no: source_line(root, path),
            });
        }
        return;
    }
    if segments[0] == "*" {
        if let Some(items) = value.as_sequence() {
            for (index, item) in items.iter().enumerate() {
                visit(
                    item,
                    &segments[1..],
                    &format!("{path}/{index}"),
                    property,
                    root,
                    violations,
                );
            }
        }
    } else if let Some(mapping) = value.as_mapping() {
        let key = serde_yaml::Value::String(segments[0].clone());
        let child_path = format!("{path}/{}", escape(&segments[0]));
        if let Some(child) = mapping.get(&key) {
            visit(
                child,
                &segments[1..],
                &child_path,
                property,
                root,
                violations,
            );
        } else if segments.len() == 1 && property.required {
            violations.push(SchemaViolation {
                field_path: child_path.clone(),
                message: format!("Missing required field '{child_path}'"),
                severity: "High".into(),
                suggested_value: String::new(),
                line_no: source_line(root, path),
            });
        }
    }
}

fn source_line(root: &SemanticNode, path: &str) -> usize {
    let mut node = root;
    for segment in path
        .trim_start_matches('/')
        .split('/')
        .filter(|part| !part.is_empty())
    {
        let next = if let Ok(index) = segment.parse::<usize>() {
            node.children.get(index)
        } else {
            node.find_node(&decode(segment))
        };
        if let Some(next) = next {
            node = next;
        } else {
            break;
        }
    }
    node.shards
        .first()
        .map(|shard| shard.line_no)
        .unwrap_or(1)
        .max(1)
}

fn matches_type(value: &serde_yaml::Value, kind: &str) -> bool {
    if let Ok(kinds) = serde_json::from_str::<Vec<String>>(kind) {
        return kinds.iter().any(|kind| matches_type(value, kind));
    }
    match kind {
        "array" => value.is_sequence(),
        "object" => value.is_mapping(),
        "string" => value.is_string(),
        "integer" => {
            value.as_i64().is_some()
                || value.as_u64().is_some()
                || value.as_str().map_or(false, |s| {
                    s.starts_with('0')
                        && s.len() > 1
                        && s.chars().all(|c| ('0'..='7').contains(&c))
                })
        }
        "number" => value.is_number(),
        "boolean" => value.is_bool(),
        "null" => value.is_null(),
        "timestamp" => value.is_string() || value.is_null(),
        "int-or-string" => {
            value.is_string() || value.as_i64().is_some() || value.as_u64().is_some()
        }
        _ => true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn validate(content: &str) -> Vec<SchemaViolation> {
        let schemas = crate::schemas::native_get_schema_for_version("1.30");
        let manifest = crate::structurer::native_structurize(crate::sharder::native_shard(content));
        crate::schemas::native_validate_ast_against_schema(&manifest, &schemas)
    }
    #[test]
    fn rejects_scalar_containers_and_nested_numeric_and_boolean_strings() {
        let bad = validate(
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers: not-a-list\n",
        );
        assert!(bad
            .iter()
            .any(|finding| finding.field_path == "/spec/containers" && finding.line_no == 6));
        let bad = validate("apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers:\n    - name: app\n      image: nginx:1.25\n      ports:\n        - containerPort: \"8080\"\n      stdin: \"true\"\n");
        assert!(bad
            .iter()
            .any(|finding| finding.field_path == "/spec/containers/0/ports/0/containerPort"));
        assert!(bad
            .iter()
            .any(|finding| finding.field_path == "/spec/containers/0/stdin"));
    }
    #[test]
    fn rejects_wrong_top_level_collection_shapes() {
        for spec in ["null", "\"text\"", "[1, 2]", "\n    - containers: []", ""] {
            let content =
                format!("apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec: {spec}\n");
            assert!(
                !validate(&content).is_empty(),
                "invalid spec accepted: {spec}"
            );
        }
    }
    #[test]
    fn accepts_block_and_flow_style_valid_containers() {
        for containers in ["\n    - name: app\n      image: nginx:1.25\n      ports:\n        - containerPort: 8080\n      stdin: true", " [{name: app, image: 'nginx:1.25', ports: [{containerPort: 8080}], stdin: true}]"] {
            let content = format!("apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\nspec:\n  containers:{containers}\n");
            assert!(validate(&content).is_empty(), "{:?}", validate(&content));
        }
    }
    #[test]
    fn stops_recursive_references_and_escapes_property_names() {
        let raw: HashMap<String, Value> = serde_json::from_value(serde_json::json!({
            "Widget": {"kind":"Widget", "fields":{"spec":{"ref":"Spec"}}},
            "Spec": {"fields":{"a/b~c":{"type":"integer"},"child":{"ref":"Spec"}}}
        }))
        .unwrap();
        let mut properties = Vec::new();
        append_nested_properties(&raw["Widget"], &raw, &mut properties);
        assert!(properties
            .iter()
            .any(|property| property.name == "/spec/a~1b~0c"));
        assert!(properties.len() < 10);
    }

    #[test]
    fn custom_schema_checks_required_fields_in_each_array_item() {
        let definition = serde_json::json!({"properties":{"spec":{"type":"object","properties":{
            "items":{"type":"array","items":{"type":"object","required":["count"],"properties":{
                "count":{"type":"integer"},"optional":{"type":"string","nullable":true}
            }}}
        }}}});
        let mut properties = Vec::new();
        append_openapi_properties(&definition, "", &mut properties);
        let schema = NativeSchema {
            kind: "Widget".into(),
            api_version: "example.test/v1".into(),
            properties,
        };
        let manifest = crate::structurer::native_structurize(crate::sharder::native_shard(
            "apiVersion: example.test/v1\nkind: Widget\nspec:\n  items:\n    - count: 3\n      optional: null\n    - optional: value\n"));
        let findings = validate_nested_properties(&manifest, &schema);
        assert_eq!(findings.len(), 1);
        assert_eq!(findings[0].field_path, "/spec/items/1/count");
        assert_eq!(findings[0].line_no, 7);
    }

    #[test]
    fn external_scalar_aliases_are_not_treated_as_objects() {
        let content = "apiVersion: v1\nkind: Service\nmetadata:\n  name: test\n  creationTimestamp: null\nspec:\n  ports:\n    - port: 80\n      targetPort: http\n";
        assert!(validate(content).is_empty(), "{:?}", validate(content));
    }

    #[test]
    fn test_empty_flow_object_on_newline() {
        let content = "apiVersion: v1\nkind: Service\nmetadata:\n  name: test\n  labels:\n    {}\nspec:\n  ports:\n    - port: 80\n";
        assert!(validate(content).is_empty(), "{:?}", validate(content));
    }
}
