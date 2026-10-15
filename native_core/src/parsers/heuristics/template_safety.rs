//! Template Safety Heuristic
//!
//! Why: GitOps manifests often contain Helm and Jinja2 template interpolations
//! (such as `{{ .Values.image.tag }}` or control blocks `{% if .Values.enabled %}`).
//! These are technically invalid YAML until rendered, but must be preserved by Yamlr's
//! forgiving lexer without punctuation distortion.

use lazy_static::lazy_static;
use regex::Regex;

lazy_static! {
    static ref RE_TEMPLATE: Regex = Regex::new(r"(\{\{.*?\}\}|\{%.*?%\}|\{#.*?\#\})").unwrap();
}

#[derive(Debug, Clone, Default)]
pub struct TemplateSafetyStatus {
    pub has_templates: bool,
    pub skip_punctuation_healing: bool,
}

/// Inspects a line for template interpolations and determines whether punctuation
/// healing should be suppressed for this line.
pub fn check_template_safety(line: &str) -> TemplateSafetyStatus {
    if RE_TEMPLATE.is_match(line) {
        let stripped = line.trim();
        let is_pure_template = (stripped.starts_with("{{") && stripped.ends_with("}}"))
            || (stripped.starts_with("{%") && stripped.ends_with("%}"))
            || (stripped.starts_with("{#") && stripped.ends_with("#}"));

        TemplateSafetyStatus {
            has_templates: true,
            skip_punctuation_healing: is_pure_template,
        }
    } else {
        TemplateSafetyStatus {
            has_templates: false,
            skip_punctuation_healing: false,
        }
    }
}

/// Normalizes duplicated or multiplied mustache template delimiters (Trap 36: `{{{{` -> `{{`, `}}}}` -> `}}`).
/// Common copy-paste or macro expansion error in Helm charts.
pub fn normalize_template_braces(line: &str) -> String {
    if !line.contains("{{{") && !line.contains("}}}") {
        return line.to_string();
    }

    let mut result = line.to_string();
    // Collapse 3 or more consecutive '{' to '{{'
    while result.contains("{{{") {
        result = result.replace("{{{", "{{");
    }
    // Collapse 3 or more consecutive '}' to '}}'
    while result.contains("}}}") {
        result = result.replace("}}}", "}}");
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detects_helm_template_expressions() {
        let status =
            check_template_safety("image: {{ .Values.image.repository }}:{{ .Values.image.tag }}");
        assert!(status.has_templates);
        assert!(!status.skip_punctuation_healing);

        let pure_block = check_template_safety("{{- if .Values.ingress.enabled }}");
        assert!(pure_block.has_templates);
        assert!(pure_block.skip_punctuation_healing);
    }

    #[test]
    fn test_normal_yaml_has_no_templates() {
        let status = check_template_safety("image: nginx:latest");
        assert!(!status.has_templates);
        assert!(!status.skip_punctuation_healing);
    }

    #[test]
    fn test_normalize_template_braces() {
        // Trap 36: Double mustache normalization
        assert_eq!(
            normalize_template_braces("image: \"{{{{ .Values.image.repository }}}}\""),
            "image: \"{{ .Values.image.repository }}\""
        );
        assert_eq!(
            normalize_template_braces("name: {{{ .Values.name }}}"),
            "name: {{ .Values.name }}"
        );
    }
}
