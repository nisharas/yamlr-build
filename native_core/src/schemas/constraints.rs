//! OpenAPI Structural Constraints and Bounds Validator.
//!
//! Why: Validates Kubernetes manifest fields against OpenAPI v3 validation keywords:
//! `pattern` (regex), `minimum`/`maximum`, `minLength`/`maxLength`, `minItems`/`maxItems`,
//! `uniqueItems`, and `multipleOf`. Prevents invalid K8s manifests from passing syntactic checks.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;

use crate::models::{SchemaViolation, SemanticNode};

/// OpenAPI structural and numerical constraint rules for a property.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PropertyConstraints {
    pub pattern: Option<String>,
    pub minimum: Option<f64>,
    pub maximum: Option<f64>,
    pub min_length: Option<usize>,
    pub max_length: Option<usize>,
    pub min_items: Option<usize>,
    pub max_items: Option<usize>,
    pub unique_items: Option<bool>,
    pub multiple_of: Option<f64>,
}

/// Validates scalar values, lengths, bounds, and array elements against constraints.
///
/// Why: Enforces Kubernetes API specifications (RFC 1123 DNS names, port ranges 1-65535,
/// replica bounds, and container name uniqueness) before manifests reach `kubectl apply`.
pub fn validate_constraints(
    field_path: &str,
    val_str: &str,
    constraints: &PropertyConstraints,
) -> Vec<SchemaViolation> {
    let mut violations = Vec::new();
    let unquoted = val_str.trim().trim_matches('"').trim_matches('\'');

    // 1. MinLength / MaxLength check
    if let Some(min_len) = constraints.min_length {
        if unquoted.chars().count() < min_len {
            violations.push(SchemaViolation {
                field_path: field_path.to_string(),
                message: format!(
                    "Constraint violation: field '{}' length {} is less than minLength {}",
                    field_path,
                    unquoted.chars().count(),
                    min_len
                ),
                severity: "Medium".to_string(),
                suggested_value: unquoted.to_string(),
                line_no: 0,
            });
        }
    }

    if let Some(max_len) = constraints.max_length {
        if unquoted.chars().count() > max_len {
            violations.push(SchemaViolation {
                field_path: field_path.to_string(),
                message: format!(
                    "Constraint violation: field '{}' length {} exceeds maxLength {}",
                    field_path,
                    unquoted.chars().count(),
                    max_len
                ),
                severity: "High".to_string(),
                suggested_value: unquoted.chars().take(max_len).collect(),
                line_no: 0,
            });
        }
    }

    // 2. Pattern (Regex) validation
    if let Some(ref pattern_str) = constraints.pattern {
        if let Ok(re) = Regex::new(pattern_str) {
            if !re.is_match(unquoted) {
                violations.push(SchemaViolation {
                    field_path: field_path.to_string(),
                    message: format!(
                        "Pattern violation: field '{}' value '{}' does not match pattern '{}'",
                        field_path, unquoted, pattern_str
                    ),
                    severity: "High".to_string(),
                    suggested_value: unquoted.to_string(),
                    line_no: 0,
                });
            }
        }
    }

    // 3. Minimum / Maximum numerical bounds
    if let Ok(num) = unquoted.parse::<f64>() {
        if let Some(min) = constraints.minimum {
            if num < min {
                violations.push(SchemaViolation {
                    field_path: field_path.to_string(),
                    message: format!(
                        "Range violation: field '{}' value {} is less than minimum {}",
                        field_path, num, min
                    ),
                    severity: "High".to_string(),
                    suggested_value: min.to_string(),
                    line_no: 0,
                });
            }
        }

        if let Some(max) = constraints.maximum {
            if num > max {
                violations.push(SchemaViolation {
                    field_path: field_path.to_string(),
                    message: format!(
                        "Range violation: field '{}' value {} exceeds maximum {}",
                        field_path, num, max
                    ),
                    severity: "High".to_string(),
                    suggested_value: max.to_string(),
                    line_no: 0,
                });
            }
        }

        if let Some(mult) = constraints.multiple_of {
            if mult > 0.0 && (num % mult).abs() > 1e-6 {
                violations.push(SchemaViolation {
                    field_path: field_path.to_string(),
                    message: format!(
                        "MultipleOf violation: field '{}' value {} is not a multiple of {}",
                        field_path, num, mult
                    ),
                    severity: "Medium".to_string(),
                    suggested_value: (num - (num % mult)).to_string(),
                    line_no: 0,
                });
            }
        }
    }

    violations
}

/// Validates array node constraints (minItems, maxItems, uniqueItems).
pub fn validate_array_constraints(
    field_path: &str,
    items: &[String],
    constraints: &PropertyConstraints,
) -> Vec<SchemaViolation> {
    let mut violations = Vec::new();

    if let Some(min_items) = constraints.min_items {
        if items.len() < min_items {
            violations.push(SchemaViolation {
                field_path: field_path.to_string(),
                message: format!(
                    "Array items violation: field '{}' contains {} items, minimum required is {}",
                    field_path,
                    items.len(),
                    min_items
                ),
                severity: "Medium".to_string(),
                suggested_value: format!("<requires {} items>", min_items),
                line_no: 0,
            });
        }
    }

    if let Some(max_items) = constraints.max_items {
        if items.len() > max_items {
            violations.push(SchemaViolation {
                field_path: field_path.to_string(),
                message: format!(
                    "Array items violation: field '{}' contains {} items, maximum allowed is {}",
                    field_path,
                    items.len(),
                    max_items
                ),
                severity: "High".to_string(),
                suggested_value: format!("<truncated to {} items>", max_items),
                line_no: 0,
            });
        }
    }

    if constraints.unique_items == Some(true) {
        let mut seen = HashSet::new();
        for item in items {
            if !seen.insert(item) {
                violations.push(SchemaViolation {
                    field_path: field_path.to_string(),
                    message: format!(
                        "Duplicate item violation: field '{}' contains duplicate entry '{}'",
                        field_path, item
                    ),
                    severity: "High".to_string(),
                    suggested_value: item.clone(),
                    line_no: 0,
                });
                break;
            }
        }
    }

    violations
}

/// Recursively validates well-known Kubernetes constraints on an AST node.
pub fn validate_k8s_builtin_constraints(root: &SemanticNode) -> Vec<SchemaViolation> {
    let mut violations = Vec::new();

    let kind = root.find_value("kind").unwrap_or_default();
    let is_rbac = kind == "ClusterRole"
        || kind == "ClusterRoleBinding"
        || kind == "Role"
        || kind == "RoleBinding";

    // 1. Check metadata.name RFC 1123 / RBAC constraint (<= 253 chars)
    if let Some(name_node) = root.find_node("metadata").and_then(|m| m.find_node("name")) {
        if let Some(ref val) = name_node.value {
            let pattern = if is_rbac {
                Some(r"^[a-zA-Z0-9_.:-]+$".to_string())
            } else {
                Some(
                    r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$"
                        .to_string(),
                )
            };
            let name_constraints = PropertyConstraints {
                pattern,
                max_length: Some(253),
                min_length: Some(1),
                ..Default::default()
            };
            violations.extend(with_source_line(
                validate_constraints("metadata.name", val, &name_constraints),
                name_node,
            ));
        }
    }

    // 2. Check metadata.namespace RFC 1123 label (<= 63 chars)
    if let Some(ns_node) = root
        .find_node("metadata")
        .and_then(|m| m.find_node("namespace"))
    {
        if let Some(ref val) = ns_node.value {
            let ns_constraints = PropertyConstraints {
                pattern: Some(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$".to_string()),
                max_length: Some(63),
                min_length: Some(1),
                ..Default::default()
            };
            violations.extend(with_source_line(
                validate_constraints("metadata.namespace", val, &ns_constraints),
                ns_node,
            ));
        }
    }

    // 3. Check port ranges (1-65535)
    for port_node in root.find_nodes_by_key_recursive("containerPort") {
        if let Some(ref val) = port_node.value {
            let port_constraints = PropertyConstraints {
                minimum: Some(1.0),
                maximum: Some(65535.0),
                ..Default::default()
            };
            violations.extend(with_source_line(
                validate_constraints("containerPort", val, &port_constraints),
                port_node,
            ));
        }
    }

    for port_node in root.find_nodes_by_key_recursive("port") {
        if let Some(ref val) = port_node.value {
            let port_constraints = PropertyConstraints {
                minimum: Some(1.0),
                maximum: Some(65535.0),
                ..Default::default()
            };
            violations.extend(with_source_line(
                validate_constraints("port", val, &port_constraints),
                port_node,
            ));
        }
    }

    // 4. Check replicas >= 0
    if let Some(spec) = root.find_node("spec") {
        if let Some(replicas_node) = spec.find_node("replicas") {
            if let Some(ref val) = replicas_node.value {
                let replica_constraints = PropertyConstraints {
                    minimum: Some(0.0),
                    ..Default::default()
                };
                violations.extend(with_source_line(
                    validate_constraints("spec.replicas", val, &replica_constraints),
                    replicas_node,
                ));
            }
        }
    }

    // 5. Container names uniqueness within pod spec
    if let Some(spec) = root.find_node("spec") {
        let containers_node = spec.find_node("containers").or_else(|| {
            spec.find_node("template")
                .and_then(|t| t.find_node("spec"))
                .and_then(|s| s.find_node("containers"))
        });

        if let Some(c_node) = containers_node {
            let mut container_names = Vec::new();
            for item in &c_node.children {
                if let Some(name_child) = item.find_node("name") {
                    if let Some(ref n) = name_child.value {
                        container_names.push(n.trim_matches('"').trim_matches('\'').to_string());
                    }
                }
            }
            if !container_names.is_empty() {
                let unique_constraints = PropertyConstraints {
                    unique_items: Some(true),
                    ..Default::default()
                };
                let mut seen_names = HashSet::new();
                let source_node = c_node
                    .children
                    .iter()
                    .find(|item| {
                        item.find_node("name")
                            .and_then(|name| name.value.as_ref())
                            .map(|name| {
                                !seen_names
                                    .insert(name.trim_matches('"').trim_matches('\'').to_string())
                            })
                            .unwrap_or(false)
                    })
                    .unwrap_or(c_node);
                violations.extend(with_source_line(
                    validate_array_constraints(
                        "spec.template.spec.containers[*].name",
                        &container_names,
                        &unique_constraints,
                    ),
                    source_node,
                ));
            }
        }
    }

    violations
}

fn with_source_line(
    mut violations: Vec<SchemaViolation>,
    source: &SemanticNode,
) -> Vec<SchemaViolation> {
    if let Some(line_no) = source
        .shards
        .first()
        .map(|shard| shard.line_no)
        .filter(|line| *line > 0)
    {
        for violation in &mut violations {
            violation.line_no = line_no;
        }
    }
    violations
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pattern_constraint_valid_and_invalid() {
        let constraints = PropertyConstraints {
            pattern: Some(r"^[a-z0-9-]+$".to_string()),
            ..Default::default()
        };
        assert!(validate_constraints("name", "valid-name-123", &constraints).is_empty());
        let bad = validate_constraints("name", "INVALID_NAME!", &constraints);
        assert_eq!(bad.len(), 1);
        assert!(bad[0].message.contains("Pattern violation"));
    }

    #[test]
    fn test_min_max_bounds() {
        let constraints = PropertyConstraints {
            minimum: Some(1.0),
            maximum: Some(65535.0),
            ..Default::default()
        };
        assert!(validate_constraints("port", "8080", &constraints).is_empty());
        let low = validate_constraints("port", "0", &constraints);
        assert_eq!(low.len(), 1);
        let high = validate_constraints("port", "70000", &constraints);
        assert_eq!(high.len(), 1);
    }

    #[test]
    fn test_string_length_bounds() {
        let constraints = PropertyConstraints {
            min_length: Some(3),
            max_length: Some(10),
            ..Default::default()
        };
        assert!(validate_constraints("tag", "stable", &constraints).is_empty());
        assert_eq!(validate_constraints("tag", "ab", &constraints).len(), 1);
        assert_eq!(
            validate_constraints("tag", "very-long-string-value", &constraints).len(),
            1
        );
    }

    #[test]
    fn test_array_unique_items() {
        let constraints = PropertyConstraints {
            unique_items: Some(true),
            ..Default::default()
        };
        let unique = vec!["app".to_string(), "sidecar".to_string()];
        assert!(validate_array_constraints("containers", &unique, &constraints).is_empty());

        let duplicates = vec!["app".to_string(), "app".to_string()];
        let bad = validate_array_constraints("containers", &duplicates, &constraints);
        assert_eq!(bad.len(), 1);
        assert!(bad[0].message.contains("Duplicate item violation"));
    }

    #[test]
    fn test_multiple_of_constraint() {
        let constraints = PropertyConstraints {
            multiple_of: Some(5.0),
            ..Default::default()
        };
        assert!(validate_constraints("count", "15", &constraints).is_empty());
        assert_eq!(validate_constraints("count", "14", &constraints).len(), 1);
    }
}
