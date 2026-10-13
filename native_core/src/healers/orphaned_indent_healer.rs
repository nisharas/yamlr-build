//! Orphaned Mapping Indentation Healer (Rule SYN-016 / Trap 71).
//!
//! Why: In Helm values files and Kubernetes manifests, users frequently comment out
//! an entire parent mapping key while leaving nested child keys indented:
//! ```yaml
//! # image:
//!   repository: registry.example.com/app
//!   tag: latest
//!
//! securityContext:
//!   enabled: false
//! ```
//! In YAML 1.2, lines 5-7 have an indentation of 2 spaces without any active parent mapping,
//! causing scanner errors: `expected <document start>, but found <block mapping start>`.
//!
//! This pre-parse heuristic detects orphaned indented mappings whose parent was commented out
//! or removed, and shifts them flush-left (to parent level 0) so the document parses cleanly.

pub const RULE_SYN_016: &str = "SYN-016";

/// Scans raw YAML and realigns orphaned indented blocks at file start to 0 indentation.
pub fn heal_orphaned_indented_blocks(raw_content: &str) -> (String, Vec<String>) {
    let mut changes = Vec::new();
    let lines: Vec<&str> = raw_content.lines().collect();
    if lines.is_empty() {
        return (raw_content.to_string(), changes);
    }

    // Check if the very first non-empty, non-comment line has an indentation > 0
    let mut first_code_idx = None;
    for (idx, line) in lines.iter().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        first_code_idx = Some((idx, line.len() - line.trim_start().len()));
        break;
    }

    if let Some((start_idx, orphan_indent)) = first_code_idx {
        if orphan_indent > 0 {
            let mut out_lines = Vec::with_capacity(lines.len());
            let mut shifted_count = 0;
            let mut in_orphan_block = true;

            for (idx, line) in lines.iter().enumerate() {
                if idx < start_idx {
                    out_lines.push(line.to_string());
                    continue;
                }

                let trimmed = line.trim();
                if trimmed.is_empty() || trimmed.starts_with('#') {
                    out_lines.push(line.to_string());
                    continue;
                }

                let current_indent = line.len() - line.trim_start().len();
                if in_orphan_block {
                    // Check if we hit a new root key (indentation 0) or document boundary
                    if current_indent == 0 || trimmed.starts_with("---") {
                        in_orphan_block = false;
                        out_lines.push(line.to_string());
                    } else if current_indent >= orphan_indent {
                        let new_indent = current_indent - orphan_indent;
                        let mut new_line = String::with_capacity(new_indent + trimmed.len());
                        new_line.push_str(&" ".repeat(new_indent));
                        new_line.push_str(trimmed);
                        out_lines.push(new_line);
                        shifted_count += 1;
                    } else {
                        in_orphan_block = false;
                        out_lines.push(line.to_string());
                    }
                } else {
                    out_lines.push(line.to_string());
                }
            }

            if shifted_count > 0 {
                changes.push(format!(
                    "Remediation [{}]: Realigned {} orphaned indented line(s) leftward to root indentation.",
                    RULE_SYN_016, shifted_count
                ));
                let delimiter = if raw_content.contains("\r\n") { "\r\n" } else { "\n" };
                return (out_lines.join(delimiter), changes);
            }
        }
    }

    (raw_content.to_string(), changes)
}

/// Rule SYN-019 / Trap 77: Strips empty flow collections (`{}` or `[]`) when immediately
/// followed on subsequent lines by block-indented child mappings/sequences.
///
/// Why: In Helm charts (e.g. `chartmuseum.yaml`), developers write:
/// ```yaml
/// annotations: {}
///   kubernetes.io/ingress.class: nginx
/// ```
/// In YAML 1.2, a mapping key whose value is `{}` is fully closed. Any following lines with
/// indentation > parent trigger parser error: `expected <block end>, but found <block mapping start>`.
/// This pre-parse healer strips `{}` or `[]` so the mapping converts cleanly into a block mapping.
pub fn heal_empty_flow_with_indented_children(raw_content: &str) -> (String, Vec<String>) {
    let mut changes = Vec::new();
    let lines: Vec<&str> = raw_content.lines().collect();
    if lines.len() < 2 {
        return (raw_content.to_string(), changes);
    }

    let mut out_lines = Vec::with_capacity(lines.len());
    let mut mutated = false;

    for (idx, line) in lines.iter().enumerate() {
        let trimmed = line.trim();
        // Check if line matches `key: {}` or `key: []`
        let is_empty_flow_key = if let Some(colon_pos) = trimmed.find(':') {
            let val = trimmed[colon_pos + 1..].trim();
            val == "{}" || val == "[]"
        } else {
            false
        };

        if is_empty_flow_key {
            let line_indent = line.len() - line.trim_start().len();
            // Look ahead to the next non-empty, non-comment line
            let mut has_indented_child = false;
            for next_line in &lines[idx + 1..] {
                let n_trim = next_line.trim();
                if n_trim.is_empty() || n_trim.starts_with('#') {
                    continue;
                }
                let next_indent = next_line.len() - next_line.trim_start().len();
                if next_indent > line_indent {
                    has_indented_child = true;
                }
                break;
            }

            if has_indented_child {
                // Strip the trailing `{}` or `[]`
                let (prefix, _) = line.split_once(':').unwrap();
                let healed_line = format!("{}:", prefix);
                out_lines.push(healed_line);
                mutated = true;
                let msg = format!(
                    "Remediation [SYN-019]: Stripped conflicting empty flow collection from '{}' preceding indented child block.",
                    trimmed.split_once(':').unwrap().0
                );
                changes.push(msg);
                continue;
            }
        }

        out_lines.push(line.to_string());
    }

    if mutated {
        let delimiter = if raw_content.contains("\r\n") { "\r\n" } else { "\n" };
        (out_lines.join(delimiter), changes)
    } else {
        (raw_content.to_string(), Vec::new())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heals_orphaned_commented_parent_block() {
        let raw = "\
# image:\n  repository: registry.example.com/app\n  tag: latest\n\nsecurityContext:\n  enabled: false\n";
        let (healed, changes) = heal_orphaned_indented_blocks(raw);
        assert!(!changes.is_empty());
        assert!(healed.contains("repository: registry.example.com/app"));
        assert!(healed.contains("tag: latest"));
        assert!(healed.contains("securityContext:"));
    }
}
