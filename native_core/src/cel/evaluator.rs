//! Kubernetes 1.30+ CEL (Common Expression Language) Policy Evaluator.
//!
//! Why: Enables evaluation of Kubernetes ValidatingAdmissionPolicy CEL expressions
//! (e.g. `object.spec.replicas <= 5`, `has(object.spec.template.spec.securityContext.runAsNonRoot)`)
//! directly inside the native Rust engine without cluster dependencies. Strictly < 500 lines.

use serde_json::Value;

/// Evaluates a CEL boolean expression against a parsed Kubernetes manifest JSON value.
pub fn eval_cel_expression(expr: &str, object: &Value) -> Result<bool, String> {
    let mut trimmed = expr.trim();

    // Strip matched outer parentheses: e.g. "(a && b)" -> "a && b"
    while trimmed.starts_with('(') && trimmed.ends_with(')') {
        let bytes = trimmed.as_bytes();
        let mut depth = 0;
        let mut fully_enclosed = true;
        for i in 0..bytes.len() - 1 {
            if bytes[i] == b'(' {
                depth += 1;
            } else if bytes[i] == b')' {
                depth -= 1;
                if depth == 0 {
                    fully_enclosed = false;
                    break;
                }
            }
        }
        if fully_enclosed {
            trimmed = trimmed[1..trimmed.len() - 1].trim();
        } else {
            break;
        }
    }

    // 1. Handle logical AND (`&&`)
    if let Some((left, right)) = split_top_level(trimmed, "&&") {
        return Ok(eval_cel_expression(left, object)? && eval_cel_expression(right, object)?);
    }

    // 2. Handle logical OR (`||`)
    if let Some((left, right)) = split_top_level(trimmed, "||") {
        return Ok(eval_cel_expression(left, object)? || eval_cel_expression(right, object)?);
    }

    // 3. Handle negation (`!expr`)
    if let Some(inner) = trimmed.strip_prefix('!') {
        return Ok(!eval_cel_expression(inner.trim(), object)?);
    }

    // 4. Handle `has(object.path.to.field)`
    if trimmed.starts_with("has(") && trimmed.ends_with(')') {
        let field_path = &trimmed[4..trimmed.len() - 1].trim();
        return Ok(resolve_cel_path(field_path, object).is_some());
    }

    // 5. Handle comparison operators: ==, !=, <=, >=, <, >
    for op in &["==", "!=", "<=", ">=", "<", ">"] {
        if let Some((left, right)) = split_top_level(trimmed, op) {
            return eval_cel_comparison(left.trim(), op, right.trim(), object);
        }
    }

    // 6. Handle boolean literals or simple truthy path
    if trimmed == "true" {
        return Ok(true);
    }
    if trimmed == "false" {
        return Ok(false);
    }

    if let Some(val) = resolve_cel_path(trimmed, object) {
        if let Some(b) = val.as_bool() {
            return Ok(b);
        }
    }

    Err(format!("Unsupported or invalid CEL expression: '{}'", expr))
}

fn eval_cel_comparison(left: &str, op: &str, right: &str, object: &Value) -> Result<bool, String> {
    let left_val = resolve_cel_literal_or_path(left, object)?;
    let right_val = resolve_cel_literal_or_path(right, object)?;

    match (left_val, right_val) {
        (Value::Number(n1), Value::Number(n2)) => {
            let num1 = n1.as_f64().unwrap_or(0.0);
            let num2 = n2.as_f64().unwrap_or(0.0);
            match op {
                "==" => Ok((num1 - num2).abs() < f64::EPSILON),
                "!=" => Ok((num1 - num2).abs() >= f64::EPSILON),
                "<=" => Ok(num1 <= num2),
                ">=" => Ok(num1 >= num2),
                "<" => Ok(num1 < num2),
                ">" => Ok(num1 > num2),
                _ => Err(format!("Unknown comparison operator: {}", op)),
            }
        }
        (Value::String(s1), Value::String(s2)) => match op {
            "==" => Ok(s1 == s2),
            "!=" => Ok(s1 != s2),
            _ => Err(format!("Operator {} not supported for strings", op)),
        },
        (Value::Bool(b1), Value::Bool(b2)) => match op {
            "==" => Ok(b1 == b2),
            "!=" => Ok(b1 != b2),
            _ => Err(format!("Operator {} not supported for booleans", op)),
        },
        (Value::Null, Value::Null) => match op {
            "==" => Ok(true),
            "!=" => Ok(false),
            _ => Ok(false),
        },
        (Value::Null, _) | (_, Value::Null) => match op {
            "==" => Ok(false),
            "!=" => Ok(true),
            _ => Ok(false),
        },
        _ => match op {
            "==" => Ok(false),
            "!=" => Ok(true),
            _ => Err(format!("Mismatched types for comparison operator {}", op)),
        },
    }
}

fn resolve_cel_literal_or_path(token: &str, object: &Value) -> Result<Value, String> {
    let t = token.trim();
    if t == "null" {
        return Ok(Value::Null);
    }
    if t == "true" {
        return Ok(Value::Bool(true));
    }
    if t == "false" {
        return Ok(Value::Bool(false));
    }
    if (t.starts_with('"') && t.ends_with('"')) || (t.starts_with('\'') && t.ends_with('\'')) {
        return Ok(Value::String(t[1..t.len() - 1].to_string()));
    }
    if let Ok(n) = t.parse::<i64>() {
        return Ok(Value::Number(n.into()));
    }
    if let Ok(f) = t.parse::<f64>() {
        if let Some(num) = serde_json::Number::from_f64(f) {
            return Ok(Value::Number(num));
        }
    }

    // Resolve as object path (e.g. object.spec.replicas or params.maxReplicas)
    match resolve_cel_path(t, object) {
        Some(v) => Ok(v.clone()),
        None => Ok(Value::Null),
    }
}

fn resolve_cel_path<'a>(path: &str, root: &'a Value) -> Option<&'a Value> {
    let clean = path.strip_prefix("object.").unwrap_or(path);
    let mut curr = root;

    for part in clean.split('.') {
        if part.is_empty() {
            continue;
        }
        match curr {
            Value::Object(map) => {
                curr = map.get(part)?;
            }
            _ => return None,
        }
    }
    Some(curr)
}

fn split_top_level<'a>(s: &'a str, delim: &str) -> Option<(&'a str, &'a str)> {
    let mut paren_depth = 0;
    let bytes = s.as_bytes();
    let d_bytes = delim.as_bytes();

    for i in 0..bytes.len() {
        if bytes[i] == b'(' {
            paren_depth += 1;
        } else if bytes[i] == b')' {
            if paren_depth > 0 {
                paren_depth -= 1;
            }
        } else if paren_depth == 0 && i + d_bytes.len() <= bytes.len() {
            if &bytes[i..i + d_bytes.len()] == d_bytes {
                let left = &s[..i];
                let right = &s[i + d_bytes.len()..];
                return Some((left, right));
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_eval_cel_basic_comparisons() {
        let manifest = serde_json::json!({
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "spec": {
                "replicas": 3,
                "template": {
                    "spec": {
                        "securityContext": {
                            "runAsNonRoot": true
                        }
                    }
                }
            }
        });

        assert_eq!(
            eval_cel_expression("object.spec.replicas <= 5", &manifest).unwrap(),
            true
        );
        assert_eq!(
            eval_cel_expression("object.spec.replicas > 10", &manifest).unwrap(),
            false
        );
        assert_eq!(
            eval_cel_expression("object.spec.replicas == 3", &manifest).unwrap(),
            true
        );
        assert_eq!(
            eval_cel_expression("object.spec.replicas != 5", &manifest).unwrap(),
            true
        );
    }

    #[test]
    fn test_eval_cel_has_macro_and_logic() {
        let manifest = serde_json::json!({
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "spec": {
                "replicas": 3,
                "template": {
                    "spec": {
                        "securityContext": {
                            "runAsNonRoot": true
                        }
                    }
                }
            }
        });

        assert_eq!(
            eval_cel_expression(
                "has(object.spec.template.spec.securityContext.runAsNonRoot)",
                &manifest
            )
            .unwrap(),
            true
        );
        assert_eq!(
            eval_cel_expression(
                "has(object.spec.template.spec.securityContext.runAsUser)",
                &manifest
            )
            .unwrap(),
            false
        );
        assert_eq!(
            eval_cel_expression(
                "has(object.spec.replicas) && object.spec.replicas < 5",
                &manifest
            )
            .unwrap(),
            true
        );
        assert_eq!(
            eval_cel_expression(
                "object.spec.replicas == 3 || object.spec.replicas == 10",
                &manifest
            )
            .unwrap(),
            true
        );
        assert_eq!(
            eval_cel_expression(
                "!has(object.spec.template.spec.securityContext.runAsUser)",
                &manifest
            )
            .unwrap(),
            true
        );
    }
}
