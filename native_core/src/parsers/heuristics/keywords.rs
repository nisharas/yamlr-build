//! Keyword Fusion & Missing Colon Heuristics
//!
//! Why: During rapid editing, developers frequently fuse keywords and values
//! (e.g., `kindService` instead of `kind: Service` or `apiVersionv1` instead of `apiVersion: v1`),
//! or omit the trailing colon on parent map headers before an indented block.

const SAFE_K8S_KEYWORDS: &[&str] = &[
    "apiVersion",
    "kind",
    "metadata",
    "spec",
    "status",
    "containers",
    "initContainers",
    "template",
    "selector",
    "ports",
    "volumeMounts",
    "volumes",
    "resources",
    "limits",
    "requests",
    "env",
    "securityContext",
    "image",
    "name",
    "namespace",
    "labels",
    "annotations",
    "rules",
    "paths",
    "serviceName",
    "servicePort",
    "replicas",
];

/// Separates fused keywords and values (e.g., `kindService` -> `kind: Service`).
pub fn apply_keyword_fusion(line: &str, in_block: bool) -> String {
    if in_block {
        return line.to_string();
    }

    let stripped = line.trim();
    if stripped.is_empty() || line.contains(':') || line.contains('[') || line.contains('{') {
        return line.to_string();
    }

    let indent_len = line.len() - line.trim_start().len();
    let indent_str = &line[..indent_len];

    for &key in SAFE_K8S_KEYWORDS {
        if stripped.starts_with(key) && stripped.len() > key.len() {
            let suffix = &stripped[key.len()..];
            // Handle space-separated: "apiVersion v1" -> suffix is " v1"
            if suffix.starts_with(' ') || suffix.starts_with('\t') {
                let trimmed_suffix = suffix.trim();
                if !trimmed_suffix.is_empty() {
                    let mut out = String::with_capacity(indent_len + key.len() + 2 + trimmed_suffix.len());
                    out.push_str(indent_str);
                    out.push_str(key);
                    out.push_str(": ");
                    out.push_str(trimmed_suffix);
                    return out;
                }
            }
            // If suffix starts with uppercase, digit, or 'v' (for apiVersion), it is fused: "apiVersionv1"
            if let Some(first_char) = suffix.chars().next() {
                if first_char.is_uppercase()
                    || first_char.is_ascii_digit()
                    || (key == "apiVersion" && (first_char == 'v' || first_char == 'V'))
                {
                    let mut out = String::with_capacity(indent_len + key.len() + 2 + suffix.len());
                    out.push_str(indent_str);
                    out.push_str(key);
                    out.push_str(": ");
                    out.push_str(suffix);
                    return out;
                }
            }
        }
    }

    line.to_string()
}

/// Injects missing colons for parent map keys based on indentation lookahead.
pub fn apply_missing_colon(line: &str, next_line: Option<&str>, in_block: bool) -> String {
    if in_block {
        return line.to_string();
    }

    let stripped = line.trim();
    if stripped.is_empty()
        || stripped.contains(':')
        || stripped.contains('[')
        || stripped.contains('{')
        || stripped.contains(';')
        || stripped.contains(' ')
        || stripped.contains('\t')
        || stripped.starts_with('-')
        || stripped.starts_with('#')
    {
        return line.to_string();
    }

    if let Some(next) = next_line {
        let next_stripped = next.trim();
        if !next_stripped.is_empty() && !next_stripped.starts_with('#') {
            let cur_indent = line.len() - line.trim_start().len();
            let next_indent = next.len() - next.trim_start().len();

            if next_indent > cur_indent {
                let mut out = line.trim_end().to_string();
                out.push(':');
                return out;
            }
        }
    }

    line.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_keyword_fusion_recovery() {
        assert_eq!(apply_keyword_fusion("kindService", false), "kind: Service");
        assert_eq!(
            apply_keyword_fusion("apiVersionv1", false),
            "apiVersion: v1"
        );
        assert_eq!(
            apply_keyword_fusion("  imageNginx", false),
            "  image: Nginx"
        );
    }

    #[test]
    fn test_missing_colon_lookahead() {
        let line = "spec";
        let next_line = "  containers:";
        assert_eq!(apply_missing_colon(line, Some(next_line), false), "spec:");

        let flat_next = "kind: Pod";
        assert_eq!(apply_missing_colon(line, Some(flat_next), false), "spec");
    }
}
