//! Over-Indented Sequence Bullet Healer (Rule SYN-017 / Trap 72).
//!
//! Why: In Helm questions.yml files and Kubernetes lists, developers frequently indent
//! sequence items inconsistently:
//! ```yaml
//! questions:
//! - variable: adminer.enabled
//!   label: Enable Adminer
//!   - variable: influxdb.enabled
//!   default: "false"
//! ```
//! The bullet `- variable: influxdb.enabled` is accidentally indented by 2 spaces relative
//! to peer items (`- variable: adminer.enabled`), triggering parser rejections:
//! `expected <block end>, but found '-'`.
//!
//! This module aligns over-indented sequence items to their peer sequence indentation.

pub const RULE_SYN_017: &str = "SYN-017";

/// Detects and realigns sequence bullets that are over-indented relative to active peer list items.
pub fn heal_overindented_sequence_items(raw_content: &str) -> (String, Vec<String>) {
    let mut changes = Vec::new();
    let lines: Vec<&str> = raw_content.lines().collect();
    if lines.is_empty() {
        return (raw_content.to_string(), changes);
    }

    // Fast-path: if the document already parses cleanly, do NOT alter list indentations!
    if serde_yaml::from_str::<serde_yaml::Value>(raw_content).is_ok() {
        return (raw_content.to_string(), changes);
    }

    let mut out_lines = Vec::with_capacity(lines.len());
    // Stack of (parent_indent, list_indent, Option<item_key_prefix>)
    let mut list_stack: Vec<(usize, String)> = Vec::new();
    let mut realigned_count = 0;

    for line in lines {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            out_lines.push(line.to_string());
            continue;
        }

        let current_indent = line.len() - line.trim_start().len();

        // Check if line starts with a list item bullet
        if trimmed.starts_with("- ") && !trimmed.starts_with("---") {
            let item_key = trimmed.split(':').next().unwrap_or("").to_string();
            if let Some((expected_indent, peer_key)) = list_stack.last() {
                if current_indent > *expected_indent && !peer_key.is_empty() && item_key == *peer_key {
                    let mut new_line = String::with_capacity(*expected_indent + trimmed.len());
                    new_line.push_str(&" ".repeat(*expected_indent));
                    new_line.push_str(trimmed);
                    out_lines.push(new_line);
                    realigned_count += 1;
                    continue;
                } else if current_indent < *expected_indent {
                    while let Some((indent, _)) = list_stack.last() {
                        if *indent > current_indent {
                            list_stack.pop();
                        } else {
                            break;
                        }
                    }
                    if list_stack.is_empty() || list_stack.last().map(|(i, _)| *i != current_indent).unwrap_or(false) {
                        list_stack.push((current_indent, item_key));
                    }
                } else if current_indent == *expected_indent {
                    // Same level peer item
                } else {
                    // Valid nested list item
                    list_stack.push((current_indent, item_key));
                }
            } else {
                list_stack.push((current_indent, item_key));
            }
        } else {
            // Non-bullet line
            while let Some((indent, _)) = list_stack.last() {
                if current_indent <= *indent {
                    list_stack.pop();
                } else {
                    break;
                }
            }
        }

        out_lines.push(line.to_string());
    }

    if realigned_count > 0 {
        let healed = out_lines.join(if raw_content.contains("\r\n") { "\r\n" } else { "\n" });
        if serde_yaml::from_str::<serde_yaml::Value>(&healed).is_ok() {
            changes.push(format!(
                "Remediation [{}]: Realigned {} over-indented sequence bullet(s) to peer indentation.",
                RULE_SYN_017, realigned_count
            ));
            return (healed, changes);
        }
    }

    (raw_content.to_string(), Vec::new())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heals_overindented_sequence_bullet() {
        let raw = "\
questions:
- variable: adminer.enabled
  label: Enable Adminer
  - variable: influxdb.enabled
  label: Enable Influxdb
";
        let (healed, changes) = heal_overindented_sequence_items(raw);
        assert!(!changes.is_empty());
        assert!(healed.contains("\n- variable: influxdb.enabled\n"));
    }
}
