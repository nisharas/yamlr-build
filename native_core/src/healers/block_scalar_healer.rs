//! Block Scalar Body Healer (Rule SYN-015 / Trap 69).
//!
//! Why: In YAML manifests, multiline literal/folded scalars (`key: |`, `key: >`)
//! require content lines to be indented deeper than the declaration key.
//! Developers frequently write script blocks or config files where the scalar content
//! starts at the exact same indentation level as the parent key:
//! ```yaml
//!   lua_scripts: |
//!   function envoy_on_response(response_handle)
//!     response_handle:headers():add("Lua-Scripts-Enabled", "Processed")
//!   end
//!   ip_allow:
//!   - peer: 127.0.0.1
//! ```
//! This violates YAML 1.2 indentation rules and causes scanner rejections:
//! `while scanning a simple key, could not find expected ':'`.
//!
//! This pre-parse/reconstruct healer detects unindented block scalar bodies and
//! safely realigns the scalar content to `key_indent + 2`, preserving comments,
//! blanks, and inner relative indentation.

use crate::parsers::heuristics::block_scalar_indentation::is_block_scalar_header;

pub const RULE_SYN_015: &str = "SYN-015";

/// Checks if a non-empty line at `indent` looks like a peer YAML key or list item
/// rather than continuation of an unindented block scalar body.
fn is_peer_key_or_boundary(line: &str, target_indent: usize) -> bool {
    let trimmed = line.trim_start();
    let indent = line.len() - trimmed.len();

    if indent < target_indent {
        return true;
    }

    if indent == target_indent {
        // Document boundary
        if trimmed.starts_with("---") || trimmed == "..." {
            return true;
        }
        // Sequence item at peer indent
        if trimmed.starts_with("- ") || trimmed == "-" {
            return true;
        }
        // Mapping key at peer indent: must have a colon followed by space or end-of-line
        if let Some(colon_idx) = trimmed.find(':') {
            let key_candidate = &trimmed[..colon_idx].trim();
            let after_colon = &trimmed[colon_idx + 1..];
            if (after_colon.is_empty() || after_colon.starts_with(' ') || after_colon.starts_with('\t'))
                && !key_candidate.contains(' ')
                && !key_candidate.contains('(')
                && !key_candidate.contains(')')
                && !key_candidate.starts_with('#')
            {
                return true;
            }
        }
    }

    false
}

/// Scans raw YAML text and normalizes unindented block scalar lines.
pub fn heal_block_scalar_indentation(raw_content: &str) -> (String, Vec<String>) {
    let mut changes = Vec::new();
    let mut lines: Vec<String> = raw_content.split('\n').map(|s| s.to_string()).collect();
    let mut i = 0;

    while i < lines.len() {
        let line = &lines[i];
        let trimmed_end = line.trim_end_matches('\r');
        let trimmed = trimmed_end.trim_start();
        let indent = trimmed_end.len() - trimmed.len();

        if !trimmed.is_empty() && is_block_scalar_header(trimmed_end) {
            let key_indent = indent;
            let target_body_indent = key_indent + 2;
            let mut j = i + 1;
            let mut unindented_count = 0;

            // Peek ahead to see if any immediate non-empty body lines are unindented (<= key_indent)
            let mut check_idx = j;
            let mut has_unindented_body = false;
            while check_idx < lines.len() {
                let next_line = &lines[check_idx];
                let next_trimmed_end = next_line.trim_end_matches('\r');
                let next_trimmed = next_trimmed_end.trim_start();
                if next_trimmed.is_empty() {
                    check_idx += 1;
                    continue;
                }
                let next_indent = next_trimmed_end.len() - next_trimmed.len();
                if is_peer_key_or_boundary(next_trimmed_end, key_indent) {
                    break;
                }
                if next_indent <= key_indent {
                    has_unindented_body = true;
                }
                check_idx += 1;
            }

            if has_unindented_body {
                // Determine shift amount: needed to lift the least-indented line up to target_body_indent
                let mut min_indent = usize::MAX;
                let mut scan_idx = j;
                while scan_idx < lines.len() {
                    let next_line = &lines[scan_idx];
                    let next_trimmed_end = next_line.trim_end_matches('\r');
                    let next_trimmed = next_trimmed_end.trim_start();
                    if next_trimmed.is_empty() {
                        scan_idx += 1;
                        continue;
                    }
                    if is_peer_key_or_boundary(next_trimmed_end, key_indent) {
                        break;
                    }
                    let next_indent = next_trimmed_end.len() - next_trimmed.len();
                    if next_indent < min_indent {
                        min_indent = next_indent;
                    }
                    scan_idx += 1;
                }

                if min_indent != usize::MAX && min_indent < target_body_indent {
                    let shift = target_body_indent - min_indent;
                    while j < lines.len() {
                        let next_line = &lines[j];
                        let ends_with_cr = next_line.ends_with('\r');
                        let next_trimmed_end = next_line.trim_end_matches('\r');
                        let next_trimmed = next_trimmed_end.trim_start();
                        if next_trimmed.is_empty() {
                            j += 1;
                            continue;
                        }
                        if is_peer_key_or_boundary(next_trimmed_end, key_indent) {
                            break;
                        }
                        let mut new_line = String::with_capacity(shift + next_trimmed_end.len() + 1);
                        new_line.push_str(&" ".repeat(shift));
                        new_line.push_str(next_trimmed_end);
                        if ends_with_cr {
                            new_line.push('\r');
                        }
                        lines[j] = new_line;
                        unindented_count += 1;
                        j += 1;
                    }

                    if unindented_count > 0 {
                        changes.push(format!(
                            "Remediation [{}]: Re-aligned {} unindented line(s) under literal block scalar header to canonical indent {}.",
                            RULE_SYN_015, unindented_count, target_body_indent
                        ));
                    }
                }
            }
            i = j;
            continue;
        }
        i += 1;
    }

    (lines.join("\n"), changes)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heals_unindented_block_scalar_body() {
        let input = r#"emissary-ingress:
  createDefaultListeners: true
  module:
    lua_scripts: |
    function envoy_on_response(response_handle)
      response_handle:headers():add("Lua-Scripts-Enabled", "Processed")
    end

    ip_allow:
    - peer: 127.0.0.1
    - remote: 99.99.0.0/16
"#;

        let (healed, changes) = heal_block_scalar_indentation(input);
        assert!(!changes.is_empty());
        assert!(healed.contains("      function envoy_on_response(response_handle)"));
        assert!(healed.contains("        response_handle:headers():add(\"Lua-Scripts-Enabled\", \"Processed\")"));
        assert!(healed.contains("      end"));
        assert!(healed.contains("    ip_allow:"));
    }

    #[test]
    fn test_idempotent_on_properly_indented_scalar() {
        let input = r#"emissary-ingress:
  module:
    lua_scripts: |
      function test()
        print("ok")
      end
    ip_allow:
    - peer: 127.0.0.1
"#;
        let (healed, changes) = heal_block_scalar_indentation(input);
        assert!(changes.is_empty());
        assert_eq!(healed, input);
    }
}
