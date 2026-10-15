//! Block Scalar Indentation Heuristic & Healing (Rule SYN-015 / Trap 69).
//!
//! Why: In YAML 1.2 and Kubernetes manifests, multiline block scalars (`|`, `>`, `|+`, `|-`)
//! require the body lines to be indented deeper than the key line.
//! Developers frequently write:
//! ```yaml
//!   lua_scripts: |
//!   function envoy_on_response(response_handle)
//!     response_handle:headers():add("Lua-Scripts-Enabled", "Processed")
//!   end
//!   ip_allow:
//!   - peer: 127.0.0.1
//! ```
//! In strict YAML parsing, scalar lines at the same indentation level as the scalar key
//! trigger scanner syntax errors (`while scanning a simple key, could not find expected ':'`).
//! This module heals unindented block scalar bodies by detecting the literal block scalar
//! declaration and re-indenting the body lines to `key_indent + 2` until the next peer key
//! or document boundary is encountered.

pub const RULE_SYN_015: &str = "SYN-015";

/// Returns true if a line represents the start of a multiline block scalar.
pub fn is_block_scalar_header(line: &str) -> bool {
    let trimmed = line.trim();
    if trimmed.starts_with('#') {
        return false;
    }
    if let Some(colon_idx) = trimmed.find(':') {
        let after_colon = trimmed[colon_idx + 1..].trim();
        // Check for indicators like |, >, |+, |-, |2, >2, etc.
        let mut chars = after_colon.chars();
        match chars.next() {
            Some('|') | Some('>') => {
                let rest = &after_colon[1..];
                rest.is_empty()
                    || rest == "+"
                    || rest == "-"
                    || rest.chars().all(|c| c.is_ascii_digit() || c == '+' || c == '-')
            }
            _ => false,
        }
    } else {
        false
    }
}

/// Computes indentation for a line in a block scalar body.
/// If `line_indent <= block_key_indent` and the line is not a peer key or doc boundary,
/// it should be shifted by `(block_key_indent + 2) - line_indent`.
pub fn heal_unindented_block_line(
    line: &str,
    line_indent: usize,
    block_key_indent: usize,
) -> String {
    let trimmed = line.trim_start();
    if trimmed.is_empty() {
        return line.to_string();
    }

    if line_indent <= block_key_indent {
        let target_indent = block_key_indent + 2;
        let mut out = String::with_capacity(target_indent + trimmed.len());
        out.push_str(&" ".repeat(target_indent));
        out.push_str(trimmed);
        out
    } else {
        line.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_block_scalar_header() {
        assert!(is_block_scalar_header("    lua_scripts: |"));
        assert!(is_block_scalar_header("  script: >-"));
        assert!(is_block_scalar_header("config: |+"));
        assert!(is_block_scalar_header("data: |2"));
        assert!(!is_block_scalar_header("key: value"));
        assert!(!is_block_scalar_header("name: test"));
    }

    #[test]
    fn test_heal_unindented_block_line() {
        let raw = "    function envoy_on_response(response_handle)";
        let healed = heal_unindented_block_line(raw, 4, 4);
        assert_eq!(healed, "      function envoy_on_response(response_handle)");

        let already_indented = "      response_handle:headers():add()";
        let kept = heal_unindented_block_line(already_indented, 6, 4);
        assert_eq!(kept, already_indented);
    }
}
