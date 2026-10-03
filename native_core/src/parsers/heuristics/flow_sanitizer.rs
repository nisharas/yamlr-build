//! Flow Style Sanitizer Heuristic
//!
//! Why: In YAML flow-style collections (e.g., `[a, b, ]` or `{key: val, }`), trailing commas
//! are technically permitted in some YAML 1.2 parsers, but cause immediate syntax errors
//! in standard Kubernetes / Python YAML parsers. This heuristic strips trailing commas
//! before closing brackets for maximum cross-parser interoperability.

use lazy_static::lazy_static;
use regex::Regex;

lazy_static! {
    static ref RE_LIST_TRAILING_COMMA: Regex = Regex::new(r",\s*\]").unwrap();
    static ref RE_MAP_TRAILING_COMMA: Regex = Regex::new(r",\s*\}").unwrap();
}

/// Removes trailing commas from flow-style lists and maps.
pub fn apply_flow_sanitizer(line: &str, in_block: bool) -> String {
    if in_block {
        return line.to_string();
    }

    if !line.contains(',') || (!line.contains(']') && !line.contains('}')) {
        return line.to_string();
    }

    let mut repaired = line.to_string();
    repaired = RE_LIST_TRAILING_COMMA
        .replace_all(&repaired, "]")
        .to_string();
    repaired = RE_MAP_TRAILING_COMMA
        .replace_all(&repaired, "}")
        .to_string();

    repaired
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_removes_trailing_comma_in_flow_list() {
        assert_eq!(
            apply_flow_sanitizer("ports: [80, 443, ]", false),
            "ports: [80, 443]"
        );
        assert_eq!(
            apply_flow_sanitizer("args: [foo, bar,   ]", false),
            "args: [foo, bar]"
        );
    }

    #[test]
    fn test_removes_trailing_comma_in_flow_map() {
        assert_eq!(
            apply_flow_sanitizer("selector: {app: web, tier: frontend, }", false),
            "selector: {app: web, tier: frontend}"
        );
    }

    #[test]
    fn test_preserves_valid_flow() {
        assert_eq!(
            apply_flow_sanitizer("ports: [80, 443]", false),
            "ports: [80, 443]"
        );
    }
}
