//! Kubernetes `x-kubernetes-validations` CEL Validation Engine.
//!
//! Why: Kubernetes 1.25+ CustomResourceDefinitions and admission schemas enforce semantic
//! invariants using Common Expression Language (CEL) via `x-kubernetes-validations`.
//! Evaluating these rules client-side catches invalid cross-field dependencies (e.g.
//! `self.minReplicas <= self.maxReplicas`) before deployment.

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::cel::evaluator::eval_cel_expression;
use crate::models::{SchemaViolation, SemanticManifest, SemanticNode};

/// An `x-kubernetes-validations` rule definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct K8sValidationRule {
    pub rule: String,
    pub message: Option<String>,
    #[serde(default)]
    pub field_path: String,
}

/// Evaluates a collection of `x-kubernetes-validations` CEL rules against a manifest.
///
/// Why: Provides pre-admission verification of complex cross-field constraints.
pub fn validate_k8s_cel_rules(
    manifest: &SemanticManifest,
    rules: &[K8sValidationRule],
) -> Vec<SchemaViolation> {
    let mut violations = Vec::new();
    let json_val = semantic_node_to_json(&manifest.root);

    for r in rules {
        let line_no = if !r.field_path.is_empty() {
            manifest
                .root
                .find_node_by_path(&r.field_path)
                .and_then(|n| n.shards.first().map(|s| s.line_no))
                .unwrap_or(0)
        } else {
            0
        };

        match evaluate_single_rule(&r.rule, &r.field_path, &json_val) {
            Ok(passed) => {
                if !passed {
                    let msg = r.message.clone().unwrap_or_else(|| {
                        format!(
                            "CEL validation failed: rule '{}' evaluated to false",
                            r.rule
                        )
                    });
                    violations.push(SchemaViolation {
                        field_path: if r.field_path.is_empty() {
                            "spec".to_string()
                        } else {
                            r.field_path.clone()
                        },
                        message: msg,
                        severity: "High".to_string(),
                        suggested_value: r.rule.clone(),
                        line_no,
                    });
                }
            }
            Err(e) => {
                violations.push(SchemaViolation {
                    field_path: if r.field_path.is_empty() {
                        "spec".to_string()
                    } else {
                        r.field_path.clone()
                    },
                    message: format!("CEL evaluation error in rule '{}': {}", r.rule, e),
                    severity: "High".to_string(),
                    suggested_value: r.rule.clone(),
                    line_no,
                });
            }
        }
    }

    violations
}

/// Evaluates a single CEL expression, substituting `self` with target field or evaluating against `object`.
pub fn evaluate_single_rule(rule: &str, field_path: &str, object: &Value) -> Result<bool, String> {
    let mut normalized_expr = rule.trim().to_string();

    // If the expression uses 'self', bind it to the relative field in the object
    if normalized_expr.contains("self") {
        let field_target = if field_path.is_empty() {
            "object"
        } else {
            field_path
        };
        let full_prefix = if field_target.starts_with("object.") {
            field_target.to_string()
        } else {
            format!("object.{}", field_target)
        };

        // Replace `self.` with `object.<path>.` and standalone `self` with `object.<path>`
        normalized_expr = normalized_expr.replace("self.", &format!("{}.", full_prefix));
        normalized_expr = normalized_expr.replace("self", &full_prefix);
    }

    eval_cel_expression(&normalized_expr, object)
}

/// Converts a SemanticNode hierarchy into a serde_json::Value for CEL evaluation.
pub fn semantic_node_to_json(node: &SemanticNode) -> Value {
    if !node.children.is_empty() {
        let mut map = serde_json::Map::new();
        for child in &node.children {
            map.insert(child.key.clone(), semantic_node_to_json(child));
        }
        Value::Object(map)
    } else if let Some(ref val) = node.value {
        let trimmed = val.trim();
        let unquoted = trimmed.trim_matches('"').trim_matches('\'');
        if let Ok(b) = unquoted.parse::<bool>() {
            Value::Bool(b)
        } else if let Ok(n) = unquoted.parse::<i64>() {
            Value::Number(serde_json::Number::from(n))
        } else if let Ok(f) = unquoted.parse::<f64>() {
            if let Some(num) = serde_json::Number::from_f64(f) {
                Value::Number(num)
            } else {
                Value::String(unquoted.to_string())
            }
        } else {
            Value::String(unquoted.to_string())
        }
    } else {
        Value::Null
    }
}

/// Evaluates standard built-in Kubernetes CEL validation rules for core workloads.
pub fn validate_builtin_cel_workloads(manifest: &SemanticManifest) -> Vec<SchemaViolation> {
    let mut rules = Vec::new();
    let json_val = semantic_node_to_json(&manifest.root);

    let kind = json_val
        .pointer("/kind")
        .and_then(|k| k.as_str())
        .unwrap_or("");

    // HorizontalPodAutoscaler: minReplicas <= maxReplicas
    if kind == "HorizontalPodAutoscaler" {
        rules.push(K8sValidationRule {
            rule: "object.spec.minReplicas <= object.spec.maxReplicas".to_string(),
            message: Some(
                "Invalid HPA: spec.minReplicas must be less than or equal to spec.maxReplicas"
                    .to_string(),
            ),
            field_path: "spec.minReplicas".to_string(),
        });
    }

    // PodDisruptionBudget: minAvailable or maxUnavailable valid
    if kind == "PodDisruptionBudget" {
        rules.push(K8sValidationRule {
            rule: "!(has(object.spec.minAvailable) && has(object.spec.maxUnavailable))".to_string(),
            message: Some(
                "Invalid PDB: spec.minAvailable and spec.maxUnavailable cannot both be specified"
                    .to_string(),
            ),
            field_path: "spec".to_string(),
        });
    }

    // Deployment / ReplicaSet: replicas >= 0
    if kind == "Deployment" || kind == "StatefulSet" || kind == "ReplicaSet" {
        rules.push(K8sValidationRule {
            rule: "!has(object.spec.replicas) || object.spec.replicas >= 0".to_string(),
            message: Some("Invalid workload: spec.replicas must be non-negative".to_string()),
            field_path: "spec.replicas".to_string(),
        });
    }

    validate_k8s_cel_rules(manifest, &rules)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_cel_self_field_evaluation() {
        let obj = serde_json::json!({
            "spec": {
                "port": 8080
            }
        });
        let res = evaluate_single_rule("self >= 1024", "spec.port", &obj);
        assert_eq!(res, Ok(true));

        let res_fail = evaluate_single_rule("self < 1024", "spec.port", &obj);
        assert_eq!(res_fail, Ok(false));
    }

    #[test]
    fn test_cel_cross_field_hpa_rule() {
        let yaml_valid = r#"
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  minReplicas: 2
  maxReplicas: 10
"#;
        let manifest_valid = native_structurize(native_shard(yaml_valid));
        let violations_valid = validate_builtin_cel_workloads(&manifest_valid);
        assert!(violations_valid.is_empty());

        let yaml_invalid = r#"
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
spec:
  minReplicas: 15
  maxReplicas: 5
"#;
        let manifest_invalid = native_structurize(native_shard(yaml_invalid));
        let violations_invalid = validate_builtin_cel_workloads(&manifest_invalid);
        assert_eq!(violations_invalid.len(), 1);
        assert!(violations_invalid[0]
            .message
            .contains("minReplicas must be less than or equal to"));
    }

    #[test]
    fn test_cel_transition_pdb_rule() {
        let yaml_invalid_pdb = r#"
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 1
  maxUnavailable: 1
"#;
        let manifest = native_structurize(native_shard(yaml_invalid_pdb));
        let violations = validate_builtin_cel_workloads(&manifest);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("cannot both be specified"));
    }

    #[test]
    fn test_cel_invalid_expr_returns_error_violation() {
        let manifest = native_structurize(native_shard("apiVersion: v1\nkind: Pod\n"));
        let bad_rule = vec![K8sValidationRule {
            rule: "%%%INVALID_SYNTAX$$$".to_string(),
            message: None,
            field_path: "spec".to_string(),
        }];
        let violations = validate_k8s_cel_rules(&manifest, &bad_rule);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].message.contains("CEL evaluation error"));
    }
}
