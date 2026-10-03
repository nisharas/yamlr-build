//! Helm Template Expander Engine.
//!
//! Why: Helm manifests contain Go template syntax (`{{ .Values.x }}`, `{{ if }}`, `{{ range }}`,
//! `{{ include }}`). Conventional K8s YAML scanners fail to parse raw unexpanded templates or
//! generate false-positive schema errors. This expander renders templates against `values.yaml`
//! prior to AST sharding and healing, enabling precise semantic validation of Helm charts.

use serde_json::Value;
use std::collections::HashMap;

/// Expands a raw Helm template string against values and optional named sub-templates.
///
/// Why: Provides an offline, hermetic Go-template approximation without requiring a `helm` CLI subprocess.
pub fn expand_helm_template(
    template: &str,
    values_yaml: &str,
    named_templates: Option<&HashMap<String, String>>,
) -> Result<String, String> {
    let values_val: Value = if values_yaml.trim().is_empty() {
        Value::Object(serde_json::Map::new())
    } else {
        serde_yaml::from_str(values_yaml)
            .map_err(|e| format!("Failed to parse values YAML: {}", e))?
    };

    let empty_map = HashMap::new();
    let templates = named_templates.unwrap_or(&empty_map);

    let context = ExpanderContext {
        root: values_val,
        templates: templates.clone(),
    };

    let tokens = tokenize_helm_template(template);
    context.render_tokens(&tokens, &context.root.clone())
}

#[derive(Debug, Clone)]
enum TemplateToken {
    Text(String),
    Expression {
        raw: String,
        #[allow(dead_code)]
        trim_left: bool,
        #[allow(dead_code)]
        trim_right: bool,
    },
    IfBlock {
        condition: String,
        then_tokens: Vec<TemplateToken>,
        else_tokens: Vec<TemplateToken>,
    },
    RangeBlock {
        iterable_expr: String,
        body_tokens: Vec<TemplateToken>,
    },
}

struct ExpanderContext {
    root: Value,
    templates: HashMap<String, String>,
}

impl ExpanderContext {
    fn render_tokens(
        &self,
        tokens: &[TemplateToken],
        current_scope: &Value,
    ) -> Result<String, String> {
        let mut out = String::new();

        for token in tokens {
            match token {
                TemplateToken::Text(txt) => out.push_str(txt),
                TemplateToken::Expression { raw, .. } => {
                    let rendered = self.eval_expression(raw, current_scope)?;
                    out.push_str(&rendered);
                }
                TemplateToken::IfBlock {
                    condition,
                    then_tokens,
                    else_tokens,
                } => {
                    let cond_val = self.eval_truthy(condition, current_scope);
                    if cond_val {
                        out.push_str(&self.render_tokens(then_tokens, current_scope)?);
                    } else {
                        out.push_str(&self.render_tokens(else_tokens, current_scope)?);
                    }
                }
                TemplateToken::RangeBlock {
                    iterable_expr,
                    body_tokens,
                } => {
                    let iter_val = self.resolve_path(iterable_expr, current_scope);
                    match iter_val {
                        Some(Value::Array(arr)) => {
                            for item in arr {
                                out.push_str(&self.render_tokens(body_tokens, item)?);
                            }
                        }
                        Some(Value::Object(map)) => {
                            for (_k, v) in map {
                                out.push_str(&self.render_tokens(body_tokens, v)?);
                            }
                        }
                        _ => {}
                    }
                }
            }
        }

        Ok(out)
    }

    fn eval_truthy(&self, expr: &str, scope: &Value) -> bool {
        let trimmed = expr.trim();
        let target = trimmed.strip_prefix("if").unwrap_or(trimmed).trim();

        if let Some(val) = self.resolve_path(target, scope) {
            match val {
                Value::Bool(b) => *b,
                Value::Null => false,
                Value::Number(n) => n.as_i64().map_or(false, |i| i != 0),
                Value::String(s) => !s.is_empty() && s != "false",
                Value::Array(a) => !a.is_empty(),
                Value::Object(m) => !m.is_empty(),
            }
        } else {
            false
        }
    }

    fn eval_expression(&self, raw: &str, scope: &Value) -> Result<String, String> {
        let trimmed = raw.trim();

        // 1. Check for include / template helper
        if trimmed.starts_with("include ") || trimmed.starts_with("template ") {
            let parts: Vec<&str> = trimmed.split_whitespace().collect();
            if parts.len() >= 2 {
                let name = parts[1].trim_matches('"').trim_matches('\'');
                if let Some(tpl_content) = self.templates.get(name) {
                    let sub_tokens = tokenize_helm_template(tpl_content);
                    return self.render_tokens(&sub_tokens, scope);
                }
            }
            return Ok(format!("# [Unresolved template: {}]", trimmed));
        }

        // 2. Handle pipelines e.g. .Values.image | default "nginx" | quote
        let pipeline_steps: Vec<&str> = trimmed.split('|').map(|s| s.trim()).collect();
        let first_expr = pipeline_steps[0];

        // If first_expr has function prefix (e.g. `nindent 4 .Values.selector` or `toYaml .Values.x`)
        let mut target_val_expr = first_expr;
        for token in first_expr.split_whitespace() {
            let clean_token = token.trim_matches('(').trim_matches(')');
            if clean_token.starts_with(".Values")
                || (clean_token.starts_with('.') && clean_token.len() > 1)
            {
                target_val_expr = clean_token;
                break;
            }
        }

        let mut current_val = self.resolve_path(target_val_expr, scope).cloned();

        for step in &pipeline_steps[1..] {
            let _ = crate::parsers::helm::sprig::eval_pipeline_step(step, &mut current_val);
        }

        if let Some(ref v) = current_val {
            match v {
                Value::String(s) => Ok(s.clone()),
                Value::Number(n) => Ok(n.to_string()),
                Value::Bool(b) => Ok(b.to_string()),
                Value::Null => Ok("".to_string()),
                other => Ok(other.to_string()),
            }
        } else if first_expr.starts_with(".Values.") {
            // Unset value default to empty or placeholder
            Ok("".to_string())
        } else if first_expr == "." {
            match scope {
                Value::String(s) => Ok(s.clone()),
                other => Ok(other.to_string()),
            }
        } else {
            Ok(trimmed.to_string())
        }
    }

    fn resolve_path<'a>(&'a self, path: &str, scope: &'a Value) -> Option<&'a Value> {
        let trimmed = path.trim();
        if trimmed == "." {
            return Some(scope);
        }

        let clean_path = if let Some(stripped) = trimmed.strip_prefix(".Values.") {
            stripped
        } else if let Some(stripped) = trimmed.strip_prefix(".Values") {
            stripped
        } else if let Some(stripped) = trimmed.strip_prefix('.') {
            stripped
        } else {
            trimmed
        };

        if clean_path.is_empty() {
            return Some(scope);
        }

        let mut current = if trimmed.starts_with(".Values") {
            &self.root
        } else {
            scope
        };

        for seg in clean_path.split('.') {
            if seg.is_empty() {
                continue;
            }
            match current {
                Value::Object(map) => {
                    if let Some(next) = map.get(seg) {
                        current = next;
                    } else {
                        return None;
                    }
                }
                _ => return None,
            }
        }

        Some(current)
    }
}

fn tokenize_helm_template(template: &str) -> Vec<TemplateToken> {
    let mut tokens = Vec::new();
    let mut rest = template;

    while let Some(start_idx) = rest.find("{{") {
        let text_before = &rest[..start_idx];
        if !text_before.is_empty() {
            tokens.push(TemplateToken::Text(text_before.to_string()));
        }

        let after_start = &rest[start_idx + 2..];
        let trim_left = after_start.starts_with('-');
        let expr_content_start = if trim_left {
            &after_start[1..]
        } else {
            after_start
        };

        if let Some(end_idx) = expr_content_start.find("}}") {
            let expr_slice = &expr_content_start[..end_idx];
            let trim_right = expr_slice.ends_with('-');
            let clean_expr = if trim_right {
                expr_slice[..expr_slice.len() - 1].trim()
            } else {
                expr_slice.trim()
            };

            tokens.push(TemplateToken::Expression {
                raw: clean_expr.to_string(),
                trim_left,
                trim_right,
            });

            rest = &expr_content_start[end_idx + 2..];
        } else {
            tokens.push(TemplateToken::Text(rest.to_string()));
            return tokens;
        }
    }

    if !rest.is_empty() {
        tokens.push(TemplateToken::Text(rest.to_string()));
    }

    assemble_blocks(tokens)
}

fn assemble_blocks(tokens: Vec<TemplateToken>) -> Vec<TemplateToken> {
    let mut result = Vec::new();
    let mut i = 0;

    while i < tokens.len() {
        match &tokens[i] {
            TemplateToken::Expression { raw, .. } if raw.starts_with("if ") => {
                let condition = raw.clone();
                let mut then_tokens = Vec::new();
                let mut else_tokens = Vec::new();
                let mut in_else = false;
                let mut nested_depth = 1;
                i += 1;

                while i < tokens.len() {
                    match &tokens[i] {
                        TemplateToken::Expression { raw: inner_raw, .. }
                            if inner_raw.starts_with("if ") =>
                        {
                            nested_depth += 1;
                            if in_else {
                                else_tokens.push(tokens[i].clone());
                            } else {
                                then_tokens.push(tokens[i].clone());
                            }
                        }
                        TemplateToken::Expression { raw: inner_raw, .. }
                            if inner_raw.trim() == "else" && nested_depth == 1 =>
                        {
                            in_else = true;
                        }
                        TemplateToken::Expression { raw: inner_raw, .. }
                            if inner_raw.trim() == "end" =>
                        {
                            nested_depth -= 1;
                            if nested_depth == 0 {
                                break;
                            }
                            if in_else {
                                else_tokens.push(tokens[i].clone());
                            } else {
                                then_tokens.push(tokens[i].clone());
                            }
                        }
                        other => {
                            if in_else {
                                else_tokens.push(other.clone());
                            } else {
                                then_tokens.push(other.clone());
                            }
                        }
                    }
                    i += 1;
                }

                result.push(TemplateToken::IfBlock {
                    condition,
                    then_tokens: assemble_blocks(then_tokens),
                    else_tokens: assemble_blocks(else_tokens),
                });
            }
            TemplateToken::Expression { raw, .. } if raw.starts_with("range ") => {
                let iterable = raw.strip_prefix("range ").unwrap_or("").trim().to_string();
                let mut body_tokens = Vec::new();
                let mut nested_depth = 1;
                i += 1;

                while i < tokens.len() {
                    match &tokens[i] {
                        TemplateToken::Expression { raw: inner_raw, .. }
                            if inner_raw.starts_with("range ") =>
                        {
                            nested_depth += 1;
                            body_tokens.push(tokens[i].clone());
                        }
                        TemplateToken::Expression { raw: inner_raw, .. }
                            if inner_raw.trim() == "end" =>
                        {
                            nested_depth -= 1;
                            if nested_depth == 0 {
                                break;
                            }
                            body_tokens.push(tokens[i].clone());
                        }
                        other => body_tokens.push(other.clone()),
                    }
                    i += 1;
                }

                result.push(TemplateToken::RangeBlock {
                    iterable_expr: iterable,
                    body_tokens: assemble_blocks(body_tokens),
                });
            }
            other => result.push(other.clone()),
        }
        i += 1;
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_expand_basic_values_substitution() {
        let tpl = "apiVersion: v1\nkind: Service\nmetadata:\n  name: {{ .Values.service.name }}\nspec:\n  port: {{ .Values.service.port }}\n";
        let vals = "service:\n  name: my-svc\n  port: 8080\n";
        let res = expand_helm_template(tpl, vals, None).unwrap();
        assert!(res.contains("name: my-svc"));
        assert!(res.contains("port: 8080"));
    }

    #[test]
    fn test_expand_conditional_if_true() {
        let tpl = "{{- if .Values.ingress.enabled -}}\nkind: Ingress\n{{- else -}}\nkind: ClusterIP\n{{- end -}}";
        let vals = "ingress:\n  enabled: true\n";
        let res = expand_helm_template(tpl, vals, None).unwrap();
        assert_eq!(res.trim(), "kind: Ingress");
    }

    #[test]
    fn test_expand_conditional_if_false() {
        let tpl = "{{- if .Values.ingress.enabled -}}\nkind: Ingress\n{{- else -}}\nkind: ClusterIP\n{{- end -}}";
        let vals = "ingress:\n  enabled: false\n";
        let res = expand_helm_template(tpl, vals, None).unwrap();
        assert_eq!(res.trim(), "kind: ClusterIP");
    }

    #[test]
    fn test_expand_range_loop() {
        let tpl = "ports:\n{{- range .Values.ports }}\n  - containerPort: {{ . }}\n{{- end }}";
        let vals = "ports:\n  - 80\n  - 443\n";
        let res = expand_helm_template(tpl, vals, None).unwrap();
        assert!(res.contains("- containerPort: 80"));
        assert!(res.contains("- containerPort: 443"));
    }

    #[test]
    fn test_expand_pipeline_default_and_quote() {
        let tpl = "image: {{ .Values.image | default \"nginx:alpine\" | quote }}\ntag: {{ .Values.missing | default \"v1.0\" }}";
        let vals = "image: \"custom-app:2.0\"\n";
        let res = expand_helm_template(tpl, vals, None).unwrap();
        assert!(res.contains("image: \"custom-app:2.0\""));
        assert!(res.contains("tag: v1.0"));
    }

    #[test]
    fn test_expand_include_named_template() {
        let tpl = "metadata:\n  {{ include \"common.labels\" . }}\n";
        let vals = "appName: demo\n";
        let mut tpls = HashMap::new();
        tpls.insert(
            "common.labels".to_string(),
            "labels:\n  app: demo".to_string(),
        );
        let res = expand_helm_template(tpl, vals, Some(&tpls)).unwrap();
        assert!(res.contains("labels:\n  app: demo"));
    }

    #[test]
    fn test_expand_unknown_function_safe_passthrough() {
        let tpl = "spec:\n  selector: {{ nindent 4 .Values.selector }}";
        let vals = "selector: app-pod\n";
        let res = expand_helm_template(tpl, vals, None).unwrap();
        assert!(res.contains("app-pod"));
    }
}
