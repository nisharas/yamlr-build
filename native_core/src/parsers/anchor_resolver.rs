//! Cross-Document YAML Anchor & Alias Pre-Pass Resolver.
//!
//! Why: In standard YAML 1.2, anchors (&name) defined in document 1 are discarded
//! across document separators (---). When a multi-document manifest (or Helm manifest)
//! defines a shared anchor in doc 1 and references it (*name) in doc 2, standard
//! parsers like serde_yaml fail with 'unknown anchor'. This resolver indexes top-level
//! anchors across all documents and inlines/re-anchors unresolved aliases across boundaries.

use std::collections::HashMap;

/// Pre-resolves cross-document YAML anchors (&anchor) across document boundaries (---).
///
/// If an alias (*name) references an anchor defined in an earlier document,
/// this resolver inlines the anchor definition locally so standard per-document
/// parsers and serde_yaml process the multi-document stream cleanly.
pub fn resolve_cross_doc_anchors(content: &str) -> (String, usize) {
    if !content.contains('&') || !content.contains('*') || !content.contains("---") {
        return (content.to_string(), 0);
    }

    let mut anchor_definitions: HashMap<String, String> = HashMap::new();
    let mut resolved_count = 0;

    // Pass 1: Extract anchors and their block definitions
    let lines: Vec<&str> = content.lines().collect();
    let mut i = 0;
    while i < lines.len() {
        let line = lines[i];
        if let Some(amp_idx) = line.find('&') {
            let after_amp = &line[amp_idx + 1..];
            let anchor_name = after_amp
                .split_whitespace()
                .next()
                .unwrap_or("")
                .trim_end_matches(':');

            if !anchor_name.is_empty() {
                // Determine indentation of the block following the anchor
                let indent_len = line.len() - line.trim_start().len();
                let mut block_lines = Vec::new();

                // If anchor is on a line like "common: &common", capture its key if needed
                let key_prefix = line[..amp_idx].trim();
                let remainder_val = after_amp[anchor_name.len()..].trim();
                if !remainder_val.is_empty() {
                    block_lines.push(remainder_val.to_string());
                }

                let mut j = i + 1;
                while j < lines.len() {
                    let next_line = lines[j];
                    if next_line.trim() == "---" {
                        break;
                    }
                    let next_indent = next_line.len() - next_line.trim_start().len();
                    if next_line.trim().is_empty() || next_indent > indent_len {
                        block_lines.push(next_line.to_string());
                        j += 1;
                    } else {
                        break;
                    }
                }

                if !block_lines.is_empty() {
                    anchor_definitions.insert(anchor_name.to_string(), block_lines.join("\n"));
                } else if !remainder_val.is_empty() {
                    anchor_definitions.insert(anchor_name.to_string(), remainder_val.to_string());
                } else if !key_prefix.is_empty() {
                    anchor_definitions.insert(anchor_name.to_string(), key_prefix.to_string());
                }
            }
        }
        i += 1;
    }

    if anchor_definitions.is_empty() {
        return (content.to_string(), 0);
    }

    // Pass 2: Trace document by document and re-anchor undefined aliases
    let mut active_anchors_in_current_doc: std::collections::HashSet<String> =
        std::collections::HashSet::new();
    let mut output_lines = Vec::with_capacity(lines.len() + 10);

    for line in lines {
        let trimmed = line.trim();
        if trimmed == "---" || trimmed.starts_with("--- ") {
            active_anchors_in_current_doc.clear();
            output_lines.push(line.to_string());
            continue;
        }

        // Register any anchors defined in the current doc
        if let Some(amp_idx) = line.find('&') {
            let after_amp = &line[amp_idx + 1..];
            if let Some(anchor_name) = after_amp.split_whitespace().next() {
                active_anchors_in_current_doc
                    .insert(anchor_name.trim_end_matches(':').to_string());
            }
        }

        // Check if line contains an alias *alias_name
        if let Some(star_idx) = line.find('*') {
            // Guard: don't confuse glob patterns like "/*" or "*" in comments
            let is_alias = star_idx == 0
                || line.as_bytes()[star_idx - 1] == b' '
                || line.as_bytes()[star_idx - 1] == b':';
            if is_alias {
                let after_star = &line[star_idx + 1..];
                let alias_name = after_star
                    .split_whitespace()
                    .next()
                    .unwrap_or("")
                    .trim_matches(|c: char| !c.is_alphanumeric() && c != '_' && c != '-');

                if !alias_name.is_empty()
                    && !active_anchors_in_current_doc.contains(alias_name)
                    && anchor_definitions.contains_key(alias_name)
                {
                    // Undefined in current document! Hoist the anchor definition right above
                    let indent = " ".repeat(line.len() - line.trim_start().len());
                    let def_block = &anchor_definitions[alias_name];

                    // Inject local anchor definition at top of current document block
                    output_lines.push(format!(
                        "{}# [Yamlr:RES-009] Local hoist of cross-document anchor &{}",
                        indent, alias_name
                    ));
                    output_lines.push(format!("{}.__yamlr_anchor_{}: &{}", indent, alias_name, alias_name));
                    for def_line in def_block.lines() {
                        output_lines.push(format!("{}  {}", indent, def_line.trim_start()));
                    }
                    active_anchors_in_current_doc.insert(alias_name.to_string());
                    resolved_count += 1;
                }
            }
        }

        output_lines.push(line.to_string());
    }

    (output_lines.join("\n"), resolved_count)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::Deserialize;

    #[test]
    fn test_cross_doc_anchor_resolution() {
        let multi_doc = r#"apiVersion: v1
kind: ConfigMap
metadata:
  name: defaults
data: &default_data
  app: myapp
  tier: frontend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  template:
    metadata:
      labels: *default_data
"#;
        let (resolved, count) = resolve_cross_doc_anchors(multi_doc);
        assert_eq!(count, 1);
        assert!(resolved.contains("&default_data"));
        assert!(resolved.contains("*default_data"));

        // Verify that serde_yaml can now deserialize every document in the multi-doc stream
        let docs: Vec<serde_yaml::Value> = serde_yaml::Deserializer::from_str(&resolved)
            .map(|d| serde_yaml::Value::deserialize(d).unwrap())
            .collect();
        assert_eq!(docs.len(), 2);
    }
}
