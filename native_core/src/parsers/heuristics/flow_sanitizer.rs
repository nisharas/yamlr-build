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

/// Sanitizes flow-style collections:
/// - Removes trailing commas: `[80, 443, ]` -> `[80, 443]`
/// - Balances mismatched bracket/brace pairs: `ports: [ 80, 443 }` -> `ports: [ 80, 443 ]`
/// - Collapses duplicated opening brackets: `env: [[ name: A, value: B }]` -> `env: [{ name: A, value: B }]`
/// - Collapses duplicated closing braces: `env: [{ name: A, value: B }}]` -> `env: [{ name: A, value: B }]`
pub fn apply_flow_sanitizer(line: &str, in_block: bool) -> String {
    if in_block {
        return line.to_string();
    }

    if !line.contains('[') && !line.contains('{') && !line.contains(']') && !line.contains('}') {
        return line.to_string();
    }

    // Step 1: Strip trailing commas
    let mut repaired = line.to_string();
    if repaired.contains(',') {
        repaired = RE_LIST_TRAILING_COMMA
            .replace_all(&repaired, "]")
            .to_string();
        repaired = RE_MAP_TRAILING_COMMA
            .replace_all(&repaired, "}")
            .to_string();
    }

    // Step 2: Balance flow brackets/braces
    repair_flow_brackets(&repaired)
}

fn repair_flow_brackets(line: &str) -> String {
    let (content_part, comment_part) = if let Some(hash_idx) = line.find('#') {
        (&line[..hash_idx], Some(&line[hash_idx..]))
    } else {
        (line, None)
    };

    let mut out = content_part.to_string();

    // 1. Repair duplicate opening bracket followed by flow mapping: `[[ {` or `[[ name:`
    // e.g. "env: [[ name: APP_ENV, value: production }]" -> "env: [{ name: APP_ENV, value: production }]"
    // e.g. "env: [[ name: APP_ENV, value: production ]]" -> "env: [{ name: APP_ENV, value: production }]"
    if out.contains("[[ ") || out.contains("[[{") {
        if out.ends_with("}]") || out.ends_with("}}]") {
            out = out.replace("[[ ", "[{ ").replace("[[{", "[{");
        }
    }

    // 2. Repair duplicate closing braces: `}}]` -> `}]`
    if out.contains("}}]") && !out.contains("{{") {
        out = out.replace("}}]", "}]");
    }

    // 3. Repair mismatched pair types: `[ ... }` -> `[ ... ]` or `{ ... ]` -> `{ ... }`
    if let Some(colon_idx) = out.find(':') {
        let val_part = out[colon_idx + 1..].trim();
        if val_part.starts_with('[') && val_part.ends_with('}') && !val_part.contains(']') {
            let prefix = &out[..out.len() - 1];
            out = format!("{}]", prefix);
        } else if val_part.starts_with('{') && val_part.ends_with(']') && !val_part.contains('}') {
            let prefix = &out[..out.len() - 1];
            out = format!("{}}}", prefix);
        }
    }

    // 4. Trap 37: Unbraced map inside flow sequence: `[ name: val, key: val ]` -> `[{ name: val, key: val }]`
    // In YAML, `[` opens a list. A bare key-value inside `[` without `{` is illegal flow syntax.
    if let Some(open_bracket) = out.find('[') {
        if let Some(close_bracket) = out.rfind(']') {
            if close_bracket > open_bracket {
                let inside = &out[open_bracket + 1..close_bracket].trim();
                // If it contains `:` and does NOT contain `{` or `}` and is not an unquoted URL
                if inside.contains(':') && !inside.contains('{') && !inside.contains('}') && !inside.starts_with("http") {
                    let pre = &out[..open_bracket + 1];
                    let post = &out[close_bracket..];
                    out = format!("{pre}{{ {inside} }}{post}");
                }
            }
        }
    }

    if let Some(c) = comment_part {
        format!("{} {}", out.trim_end(), c.trim_start())
    } else {
        out
    }
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

    #[test]
    fn test_bracket_asymmetry_and_pairs() {
        // Mismatched outer bracket [[ ... }]
        assert_eq!(
            apply_flow_sanitizer("env: [[ name: APP_ENV, value: production }]", false),
            "env: [{ name: APP_ENV, value: production }]"
        );

        // Mismatched inner brace [{ ... }}]
        assert_eq!(
            apply_flow_sanitizer("env: [{ name: APP_ENV, value: production }}]", false),
            "env: [{ name: APP_ENV, value: production }]"
        );

        // Mismatched pair types [ ... }
        assert_eq!(
            apply_flow_sanitizer("ports: [80, 443}", false),
            "ports: [80, 443]"
        );

        // Trap 37: Unbraced map inside flow sequence
        assert_eq!(
            apply_flow_sanitizer("env: [ name: APP_ENV, value: production ]", false),
            "env: [{ name: APP_ENV, value: production }]"
        );
        assert_eq!(
            apply_flow_sanitizer("ports: [ containerPort: 80, protocol: TCP ]", false),
            "ports: [{ containerPort: 80, protocol: TCP }]"
        );
    }
}
