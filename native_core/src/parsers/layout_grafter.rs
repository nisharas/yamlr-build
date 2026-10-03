//! Sovereign Layout Restoration Engine (Layout Grafter)
//!
//! Why: In complex AST surgeries and transformations, line numbers shift and synthetic
//! nodes are injected. The Layout Grafter re-anchors original human comments, whitespace,
//! and layout sequences onto the modified shards using a 3-tier matching protocol:
//! 1. Line-Identity (exact line number match)
//! 2. Epistemic (dot-path re-anchoring, e.g. `metadata.labels.app`)
//! 3. Geometric (neighbor context `geo:prev_key|next_key`)

use crate::models::NativeShard;
use crate::sharder::native_shard;
use std::collections::HashMap;

/// Sovereign Layout Restoration Engine.
pub struct LayoutGrafter;

impl LayoutGrafter {
    /// Derives the dot-path for a given shard within the hierarchy stack.
    ///
    /// Why: Dot-paths bridge the reincarnation gap when AST surgery changes line numbers.
    pub fn derive_node_path(stack: &[(usize, String)], shard: &NativeShard) -> String {
        let parent_path = stack.last().map(|(_, p)| p.as_str()).unwrap_or("");

        if shard.is_list_item {
            if shard.key.is_empty() {
                if let Some(val) = &shard.value {
                    let clean_val = val.trim_matches(|c| c == '"' || c == '\'');
                    if parent_path.is_empty() {
                        format!("[0].{}", clean_val)
                    } else {
                        format!("{}.[0].{}", parent_path, clean_val)
                    }
                } else if parent_path.is_empty() {
                    "[0]".to_string()
                } else {
                    format!("{}.[0]", parent_path)
                }
            } else if parent_path.is_empty() {
                format!("[0].{}", shard.key)
            } else {
                format!("{}.[0].{}", parent_path, shard.key)
            }
        } else if shard.key.is_empty() {
            parent_path.to_string()
        } else if parent_path.is_empty() {
            shard.key.clone()
        } else {
            format!("{}.{}", parent_path, shard.key)
        }
    }

    /// Derives dot-paths for all shards in the given slice.
    pub fn build_path_map(shards: &[NativeShard]) -> HashMap<String, usize> {
        let mut path_map = HashMap::new();
        let mut stack: Vec<(usize, String)> = Vec::new();

        for (idx, s) in shards.iter().enumerate() {
            if s.is_doc_boundary {
                stack.clear();
                continue;
            }

            while !stack.is_empty() && stack.last().unwrap().0 >= s.indent {
                stack.pop();
            }

            let current_path = Self::derive_node_path(&stack, s);
            if !current_path.is_empty() {
                path_map.entry(current_path.clone()).or_insert(idx);
            }

            if s.value.is_none() || s.is_block {
                stack.push((s.indent, current_path));
            }
        }

        path_map
    }

    /// Derives geometric neighbor tags (`geo:prev_key|next_key`) for shards.
    pub fn build_geometric_map(shards: &[NativeShard]) -> HashMap<String, usize> {
        let mut geo_map = HashMap::new();

        for (i, s) in shards.iter().enumerate() {
            if s.key.is_empty() || s.is_doc_boundary {
                continue;
            }

            // Find previous sibling at the same indent
            let mut prev_key = "none";
            for j in (0..i).rev() {
                if shards[j].indent < s.indent {
                    break;
                }
                if shards[j].indent == s.indent && !shards[j].key.is_empty() {
                    prev_key = &shards[j].key;
                    break;
                }
            }

            // Find next sibling at the same indent
            let mut next_key = "none";
            for j in (i + 1)..shards.len() {
                if shards[j].indent < s.indent {
                    break;
                }
                if shards[j].indent == s.indent && !shards[j].key.is_empty() {
                    next_key = &shards[j].key;
                    break;
                }
            }

            let geo_tag = format!("geo:{}|{}", prev_key, next_key);
            geo_map.entry(geo_tag).or_insert(i);
        }

        geo_map
    }

    /// Restores layout metadata (comments, gaps, blank lines) from raw content onto shards.
    pub fn graft(content: &str, shards: &mut Vec<NativeShard>) {
        if shards.is_empty() {
            return;
        }

        // Shard reference mapping for original content
        let orig_shards = native_shard(content);
        let orig_path_map = Self::build_path_map(&orig_shards);

        // Target shard lookup maps
        let mut target_line_map: HashMap<usize, usize> = HashMap::new();
        for (idx, s) in shards.iter().enumerate() {
            if s.line_no > 0 {
                target_line_map.insert(s.line_no, idx);
            }
        }
        let target_path_map = Self::build_path_map(shards);
        let target_geo_map = Self::build_geometric_map(shards);

        // Walk through original lines, collecting layout buffers (whitespace & comments)
        let mut layout_buffer: Vec<String> = Vec::new();
        let orig_lines: Vec<&str> = content.lines().collect();

        for (line_idx, line) in orig_lines.iter().enumerate() {
            let mut line_normalized = *line;
            if line_idx == 0 && line_normalized.starts_with('\u{feff}') {
                line_normalized = &line_normalized[3..];
            }

            let trimmed = line_normalized.trim();
            let line_no = line_idx + 1;

            if trimmed.is_empty() {
                layout_buffer.push(line.to_string());
                continue;
            }

            // Standalone comment line
            if trimmed.starts_with('#') {
                if let Some(&idx) = target_line_map.get(&line_no) {
                    if !layout_buffer.is_empty() {
                        Self::append_layout_dedup(
                            &mut shards[idx].layout_sequence,
                            &mut layout_buffer,
                        );
                    }
                } else {
                    layout_buffer.push(line.to_string());
                }
                continue;
            }

            // We reached a code line in original content.
            // Determine where layout_buffer should be grafted in `shards`.
            if !layout_buffer.is_empty() {
                let target_idx = Self::resolve_target_shard_index(
                    line_no,
                    &orig_shards,
                    &orig_path_map,
                    &target_line_map,
                    &target_path_map,
                    &target_geo_map,
                    shards,
                );

                if let Some(idx) = target_idx {
                    Self::append_layout_dedup(&mut shards[idx].layout_sequence, &mut layout_buffer);
                } else if let Some(last_shard) = shards.iter_mut().find(|s| !s.is_doc_boundary) {
                    Self::append_layout_dedup(&mut last_shard.layout_sequence, &mut layout_buffer);
                }
            }
        }

        // EOF orphan restoration
        if !layout_buffer.is_empty() {
            if let Some(last_shard) = shards.iter_mut().rev().find(|s| !s.is_doc_boundary) {
                Self::append_layout_dedup(
                    &mut last_shard.trailing_layout_sequence,
                    &mut layout_buffer,
                );
            }
        }
    }

    /// Resolves the best target shard index using Identity, Epistemic, and Geometric tiers.
    fn resolve_target_shard_index(
        orig_line_no: usize,
        orig_shards: &[NativeShard],
        orig_path_map: &HashMap<String, usize>,
        target_line_map: &HashMap<usize, usize>,
        target_path_map: &HashMap<String, usize>,
        target_geo_map: &HashMap<String, usize>,
        target_shards: &[NativeShard],
    ) -> Option<usize> {
        // Tier 1: Identity Match (Exact line number)
        if let Some(&idx) = target_line_map.get(&orig_line_no) {
            return Some(idx);
        }

        // Find original shard at this line to compute dot-path / geo-tag
        let orig_shard = orig_shards.iter().find(|s| s.line_no == orig_line_no)?;

        // Tier 2: Epistemic Match (Dot-path)
        for (path, &orig_idx) in orig_path_map.iter() {
            if orig_idx < orig_shards.len() && orig_shards[orig_idx].line_no == orig_line_no {
                if let Some(&target_idx) = target_path_map.get(path) {
                    return Some(target_idx);
                }
            }
        }

        // Tier 3: Geometric Match (Neighbor context)
        if !orig_shard.key.is_empty() {
            // Find previous and next sibling of orig_shard
            let orig_pos = orig_shards.iter().position(|s| s.line_no == orig_line_no)?;
            let mut prev_key = "none";
            for j in (0..orig_pos).rev() {
                if orig_shards[j].indent < orig_shard.indent {
                    break;
                }
                if orig_shards[j].indent == orig_shard.indent && !orig_shards[j].key.is_empty() {
                    prev_key = &orig_shards[j].key;
                    break;
                }
            }
            let mut next_key = "none";
            for j in (orig_pos + 1)..orig_shards.len() {
                if orig_shards[j].indent < orig_shard.indent {
                    break;
                }
                if orig_shards[j].indent == orig_shard.indent && !orig_shards[j].key.is_empty() {
                    next_key = &orig_shards[j].key;
                    break;
                }
            }
            let geo_tag = format!("geo:{}|{}", prev_key, next_key);
            if let Some(&idx) = target_geo_map.get(&geo_tag) {
                return Some(idx);
            }
        }

        // Fallback: nearest shard
        target_shards
            .iter()
            .position(|s| s.indent == orig_shard.indent)
    }

    /// Appends lines from buffer into target sequence with deduplication.
    fn append_layout_dedup(target: &mut Vec<String>, buffer: &mut Vec<String>) {
        for line in buffer.drain(..) {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                target.push(line);
            } else if !target.iter().any(|existing| existing.trim() == trimmed) {
                target.push(line);
            }
        }
    }
}

/// Applies the LayoutGrafter to restore layout metadata onto shards.
pub fn native_apply_layout_grafter(content: &str, shards: &mut Vec<NativeShard>) {
    LayoutGrafter::graft(content, shards);
}

/// Utility function applying all 12 lexical heuristics across the manifest lines.
pub fn native_apply_heuristics(content: &str) -> String {
    let mut result = Vec::new();
    let lines: Vec<&str> = content.lines().collect();
    let mut in_block = false;
    let mut block_indent = 0;
    let mut parent_indent: Option<usize> = None;

    for (i, line) in lines.iter().enumerate() {
        let trimmed = line.trim();
        let current_indent = line.len() - line.trim_start().len();

        if in_block {
            if !trimmed.is_empty() && current_indent <= block_indent {
                in_block = false;
            } else {
                result.push(line.to_string());
                continue;
            }
        }

        if trimmed.ends_with('|') || trimmed.ends_with('>') {
            in_block = true;
            block_indent = current_indent;
            result.push(line.to_string());
            continue;
        }

        let next_line = lines.get(i + 1).copied();
        let processed =
            crate::parsers::heuristics::preprocess_line(line, next_line, parent_indent, in_block);

        if trimmed.ends_with(':') {
            parent_indent = Some(current_indent);
        }

        result.push(processed);
    }
    result.join("\n")
}

/// Applies shadow layout sequences directly onto parsed shards.
pub fn native_apply_shadow(content: &str, shards: &mut Vec<NativeShard>) {
    let mut layout_buffer = Vec::new();
    let mut shard_map = HashMap::new();
    for (i, shard) in shards.iter().enumerate() {
        shard_map.insert(shard.line_no, i);
    }

    for (i, line) in content.lines().enumerate() {
        let mut line_normalized = line.to_string();

        // Strip UTF-8 BOM if present on the first line
        if i == 0 && line_normalized.starts_with('\u{feff}') {
            line_normalized = line_normalized[3..].to_string();
        }

        let trimmed = line_normalized.trim();
        let line_no = i + 1;

        if trimmed.is_empty() {
            layout_buffer.push(line.to_string());
            continue;
        }

        if trimmed.starts_with('#') {
            if !shard_map.contains_key(&line_no) {
                layout_buffer.push(line.to_string());
                continue;
            }
        }

        if let Some(&shard_idx) = shard_map.get(&line_no) {
            let shard = &mut shards[shard_idx];
            if !shard.is_doc_boundary {
                shard.layout_sequence.append(&mut layout_buffer);
            }
        }
    }

    if !layout_buffer.is_empty() {
        if let Some(last_shard) = shards.iter_mut().rev().find(|s| !s.is_doc_boundary) {
            last_shard
                .trailing_layout_sequence
                .append(&mut layout_buffer);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_layout_grafter_preserves_comments() {
        let content = "# Header comment\n# Second line\napiVersion: v1\nkind: Pod";
        // Simulate AST tree where standalone comment shards are not separate nodes
        let mut shards: Vec<NativeShard> = native_shard(content)
            .into_iter()
            .filter(|s| !s.key.is_empty())
            .collect();
        native_apply_layout_grafter(content, &mut shards);

        assert!(!shards[0].layout_sequence.is_empty());
        assert!(shards[0]
            .layout_sequence
            .iter()
            .any(|l| l.contains("# Header comment")));
        assert!(shards[0]
            .layout_sequence
            .iter()
            .any(|l| l.contains("# Second line")));
    }

    #[test]
    fn test_layout_grafter_epistemic_reanchoring() {
        let content = "metadata:\n  # Important label comment\n  labels:\n    app: test";
        let mut shards = native_shard(content);

        // Simulate surgical shard modification: reset line numbers to 0
        for s in shards.iter_mut() {
            s.line_no = 0;
        }

        native_apply_layout_grafter(content, &mut shards);

        // The labels shard or app shard should receive the label comment via dot-path matching
        let has_comment = shards.iter().any(|s| {
            s.layout_sequence
                .iter()
                .any(|l| l.contains("# Important label comment"))
        });
        assert!(
            has_comment,
            "Comment should be re-anchored via epistemic dot-path matching"
        );
    }

    #[test]
    fn test_layout_grafter_trailing_eof_preservation() {
        let content = "apiVersion: v1\nkind: Pod\n# Trailing EOF note\n";
        let mut shards: Vec<NativeShard> = native_shard(content)
            .into_iter()
            .filter(|s| !s.key.is_empty())
            .collect();
        native_apply_layout_grafter(content, &mut shards);

        let last_shard = shards.last().unwrap();
        assert!(
            last_shard
                .trailing_layout_sequence
                .iter()
                .any(|l| l.contains("# Trailing EOF note")),
            "Trailing EOF comment should be preserved in trailing_layout_sequence"
        );
    }

    #[test]
    fn test_native_apply_heuristics_all_passes() {
        let raw = "\tkindService\n\tenabled:yes\n  image nginx";
        let healed = native_apply_heuristics(raw);
        assert!(healed.contains("kind: Service"), "Healed: {}", healed);
        assert!(healed.contains("enabled: \"yes\""), "Healed: {}", healed);
        assert!(healed.contains("image: nginx"), "Healed: {}", healed);
    }
}
