//! Malformed Anchor Line Colon Attachment Healer (Rule SYN-018 / Trap 73).
//!
//! Why: In Helm and Kubernetes manifests using YAML anchors and merge keys (<<: *anchor),
//! authors frequently place the anchor on its own line under a parent key with an accidental
//! trailing colon:
//! ```yaml
//! context:
//!   &context: # Name of the global scope
//!   scope: myscope
//! ```
//! In YAML 1.2, `&context:` defines a mapping key whose name is empty and whose anchor is `context`,
//! resulting in a scalar string node rather than anchoring the mapping body below it.
//! When merged via `<<: *context`, YAML parsers reject it with:
//! `expected a mapping or list of mappings for merging, but found scalar`.
//!
//! This module normalizes isolated anchor definition keys `&anchor:` under mapping keys to attach
//! cleanly to the parent mapping: `context: &context`.

pub const RULE_SYN_018: &str = "SYN-018";

/// Detects and normalizes malformed standalone anchor lines under parent mappings.
pub fn heal_malformed_anchor_declarations(raw_content: &str) -> (String, Vec<String>) {
    let mut changes = Vec::new();
    let lines: Vec<&str> = raw_content.lines().collect();
    if lines.is_empty() || !raw_content.contains('&') {
        return (raw_content.to_string(), changes);
    }

    let mut out_lines = Vec::with_capacity(lines.len());
    let mut i = 0;
    let mut healed_count = 0;

    while i < lines.len() {
        let line = lines[i];
        let trimmed = line.trim();

        // Check if line is a parent mapping key with no value (e.g. `context:`)
        if !trimmed.starts_with('#') && trimmed.ends_with(':') && !trimmed.contains(' ') && i + 1 < lines.len() {
            let parent_indent = line.len() - line.trim_start().len();
            let parent_key = trimmed.trim_end_matches(':');

            // Look ahead to next non-comment line
            let mut j = i + 1;
            while j < lines.len() && (lines[j].trim().is_empty() || lines[j].trim().starts_with('#')) {
                j += 1;
            }

            if j < lines.len() {
                let next_line = lines[j];
                let next_trimmed = next_line.trim();
                let next_indent = next_line.len() - next_line.trim_start().len();

                // Check if next line is a standalone anchor key like `&context:` or `&anchor:`
                if next_indent > parent_indent && next_trimmed.starts_with('&') {
                    let anchor_part = next_trimmed.split_whitespace().next().unwrap_or("");
                    if anchor_part.ends_with(':') {
                        let anchor_name = anchor_part.trim_start_matches('&').trim_end_matches(':');
                        let comment_part = if let Some(hash_pos) = next_trimmed.find('#') {
                            format!(" {}", &next_trimmed[hash_pos..])
                        } else {
                            String::new()
                        };

                        // Merge into parent line: `context: &context # comment`
                        let indent_spaces = " ".repeat(parent_indent);
                        let fused_parent = format!("{}{}: &{}{}", indent_spaces, parent_key, anchor_name, comment_part);
                        out_lines.push(fused_parent);

                        // Push any blank/comment lines that occurred between i and j
                        for k in (i + 1)..j {
                            out_lines.push(lines[k].to_string());
                        }

                        healed_count += 1;
                        i = j + 1;
                        continue;
                    }
                }
            }
        }

        out_lines.push(line.to_string());
        i += 1;
    }

    if healed_count > 0 {
        changes.push(format!(
            "Remediation [{}]: Realigned {} malformed standalone anchor declaration(s) to parent mapping header.",
            RULE_SYN_018, healed_count
        ));
        let delimiter = if raw_content.contains("\r\n") { "\r\n" } else { "\n" };
        return (out_lines.join(delimiter), changes);
    }

    (raw_content.to_string(), changes)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heals_standalone_anchor_colon_line() {
        let raw = "\
context:
  &context: # Name of the global scope
  scope: myscope
  cluster: default
project:
  context:
    <<: *context
";
        let (healed, changes) = heal_malformed_anchor_declarations(raw);
        assert_eq!(changes.len(), 1);
        assert!(healed.contains("context: &context # Name of the global scope"));
        assert!(!healed.contains("  &context:"));
    }
}
