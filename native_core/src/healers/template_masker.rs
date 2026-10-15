//! Helm & Go Template Expression Masker (Feature 14 of 15).
//!
//! Why: Helm charts heavily rely on Go template directives (e.g. `{{ .Values.image }}`,
//! `{{- if .Values.enabled }}`). Standard YAML parsers reject or corrupt unquoted curly
//! braces as malformed flow mappings.
//!
//! This module replaces template expressions with deterministic placeholder tokens during
//! parsing and reconstruction, restoring them byte-for-byte post-healing.

use std::collections::HashMap;

#[derive(Debug, Clone, Default)]
pub struct TemplateMaskRegistry {
    pub placeholders: HashMap<String, String>,
}

/// Masks Helm/Go template expressions `{{ ... }}` in raw YAML content.
pub fn mask_template_expressions(content: &str) -> (String, TemplateMaskRegistry) {
    let mut registry = TemplateMaskRegistry::default();
    let mut masked_lines = Vec::new();
    let mut counter = 0;

    for line in content.lines() {
        let trimmed = line.trim();

        // Standalone Helm control lines (e.g. `{{- if ... }}`, `{{- end }}`)
        if trimmed.starts_with("{{") && trimmed.ends_with("}}") {
            let token = format!("# __YAMLR_HELM_CTRL_{}__", counter);
            registry
                .placeholders
                .insert(token.clone(), line.to_string());
            masked_lines.push(token);
            counter += 1;
            continue;
        }

        // Dynamic key expressions (e.g. `{{ .Values.key }}: value`)
        // Ensure token produces a valid alphanumeric key identifier
        if line.contains("{{") && line.contains("}}") {
            let mut line_buf = String::new();
            let mut remaining = line;

            while let Some(start_idx) = remaining.find("{{") {
                line_buf.push_str(&remaining[..start_idx]);
                let after_start = &remaining[start_idx..];

                if let Some(end_idx) = after_start.find("}}") {
                    let full_expr = &after_start[..end_idx + 2];
                    let is_key_position = after_start[end_idx + 2..].trim_start().starts_with(':');
                    let token = if is_key_position {
                        format!("yamlr_tpl_key_{}__", counter)
                    } else {
                        format!("__YAMLR_TPL_VAL_{}__", counter)
                    };
                    counter += 1;

                    registry
                        .placeholders
                        .insert(token.clone(), full_expr.to_string());
                    line_buf.push_str(&token);
                    remaining = &after_start[end_idx + 2..];
                } else {
                    line_buf.push_str(after_start);
                    remaining = "";
                    break;
                }
            }
            line_buf.push_str(remaining);
            masked_lines.push(line_buf);
        } else {
            masked_lines.push(line.to_string());
        }
    }

    let sep = if content.contains("\r\n") {
        "\r\n"
    } else {
        "\n"
    };
    let mut result = masked_lines.join(sep);
    if content.ends_with('\n') && !result.is_empty() {
        result.push_str(if content.ends_with("\r\n") {
            "\r\n"
        } else {
            "\n"
        });
    }
    (result, registry)
}

/// Restores original Helm/Go template expressions from placeholders.
pub fn unmask_template_expressions(content: &str, registry: &TemplateMaskRegistry) -> String {
    let mut restored = content.to_string();

    let mut tokens: Vec<(&String, &String)> = registry.placeholders.iter().collect();
    tokens.sort_by(|a, b| b.0.len().cmp(&a.0.len()));

    for (token, original_expr) in tokens {
        restored = restored.replace(token, original_expr);
    }
    restored
}

/// Returns true if the given string contains a Helm/Go template control placeholder or token.
pub fn is_dynamic_block_token(text: &str) -> bool {
    text.contains("__YAMLR_HELM_CTRL_")
        || text.contains("__YAMLR_TPL_VAL_")
        || text.contains("yamlr_tpl_key_")
        || text.contains("yamlr-tpl-token-")
}

/// Returns true if a SemanticNode or any of its shards/children is driven by a dynamic template directive (e.g. toYaml, include).
pub fn contains_dynamic_block(node: &crate::models::SemanticNode) -> bool {
    for s in &node.shards {
        if is_dynamic_block_token(&s.raw_line) || is_dynamic_block_token(&s.comment) {
            return true;
        }
        if let Some(v) = &s.value {
            if is_dynamic_block_token(v) {
                return true;
            }
        }
    }
    for c in &node.children {
        if is_dynamic_block_token(&c.key) {
            return true;
        }
        if let Some(v) = &c.value {
            if is_dynamic_block_token(v) {
                return true;
            }
        }
        if contains_dynamic_block(c) {
            return true;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mask_and_unmask_inline_template() {
        let raw = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: {{ .Values.podName }}\nspec:\n  containers:\n    - name: web\n      image: {{ .Values.image.repo }}:{{ .Values.image.tag }}\n";
        let (masked, registry) = mask_template_expressions(raw);

        assert!(!masked.contains("{{"));
        assert!(!masked.contains("}}"));
        assert_eq!(registry.placeholders.len(), 3);

        let unmasked = unmask_template_expressions(&masked, &registry);
        assert_eq!(unmasked, raw);
    }

    #[test]
    fn test_mask_and_unmask_standalone_control_line() {
        let raw = "apiVersion: v1\nkind: Service\n{{- if .Values.service.enabled }}\nmetadata:\n  name: my-svc\n{{- end }}";
        let (masked, registry) = mask_template_expressions(raw);

        assert!(masked.contains("# __YAMLR_HELM_CTRL_0__"));
        let unmasked = unmask_template_expressions(&masked, &registry);
        assert_eq!(unmasked, raw);
    }

    #[test]
    fn test_dynamic_block_detection() {
        assert!(is_dynamic_block_token("# __YAMLR_HELM_CTRL_0__"));
        assert!(is_dynamic_block_token("yamlr-tpl-token-1"));
        assert!(!is_dynamic_block_token("regular-string"));
    }
}
