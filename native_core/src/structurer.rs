#![forbid(unsafe_code)]

use crate::models::*;

#[derive(Debug, Clone, Default)]
struct ArenaNode {
    key: String,
    value: Option<String>,
    children: Vec<usize>,
    shards: Vec<NativeShard>,
    indent: usize,
    is_empty_flow: bool,
}

/// Builds a semantic tree from tokenized shards.
///
/// Reconstructs a hierarchical semantic tree from a linear stream of shards
/// using an Index-Based Arena Tree. Guaranteed 100% memory-safe (zero `unsafe` blocks),
/// resistant to reallocation pointer corruption, and deterministic.
pub fn native_structurize(shards: Vec<NativeShard>) -> SemanticManifest {
    let mut arena: Vec<ArenaNode> = Vec::with_capacity(shards.len() + 1);

    // Root node is always at index 0
    arena.push(ArenaNode {
        key: "root".to_string(),
        value: None,
        children: Vec::new(),
        shards: Vec::new(),
        indent: 0,
        is_empty_flow: false,
    });

    let mut detected_step = 2;
    let mut first_indent = None;

    // Stack tracks: (indent_level, arena_index)
    let mut stack: Vec<(usize, usize)> = Vec::new();
    stack.push((0, 0));

    let mut integrity_violations = Vec::new();

    for shard in shards {
        if shard.is_doc_boundary {
            continue;
        }

        // --- Multiline Block Awareness / Table continuation ---
        if shard.is_table_continuation {
            if let Some(&(_, parent_idx)) = stack.last() {
                if let Some(&last_child_idx) = arena[parent_idx].children.last() {
                    arena[last_child_idx].shards.push(shard.clone());
                }
            }
            continue;
        }

        let shard_indent = shard.indent;

        // Detect indent step from the first indented child of root
        if shard_indent > 0 && first_indent.is_none() {
            first_indent = Some(shard_indent);
            detected_step = shard_indent;
        }

        // Pop stack until we find the parent level
        while !stack.is_empty() && stack.len() > 1 {
            let (top_indent, top_idx) = *stack.last().unwrap();
            let top_is_list_item = arena[top_idx]
                .shards
                .first()
                .map_or(false, |s| s.is_list_item);

            if shard.is_list_item {
                if top_is_list_item {
                    if top_indent >= shard_indent {
                        stack.pop();
                    } else {
                        break;
                    }
                } else {
                    if top_indent > shard_indent {
                        stack.pop();
                    } else {
                        break;
                    }
                }
            } else {
                if top_indent >= shard_indent {
                    stack.pop();
                } else {
                    break;
                }
            }
        }

        if let Some(&(_, parent_idx)) = stack.last() {
            let mut node_key = shard.key.clone();
            if shard.is_list_item && node_key.is_empty() {
                node_key = "-".to_string();
            }

            // Semantic Unquoting
            if (node_key.starts_with('"') && node_key.ends_with('"'))
                || (node_key.starts_with('\'') && node_key.ends_with('\''))
            {
                if node_key.len() >= 2 {
                    node_key = node_key[1..node_key.len() - 1].to_string();
                }
            }

            // Semantic Key Interning: if node_key matches known static K8s key, reuse static str
            if let Some(interned) = crate::parsers::interner::intern_k8s_key(&node_key) {
                node_key = interned.to_string();
            }

            // Duplicate Sibling Detection
            if !node_key.is_empty() && node_key != "-" {
                let is_duplicate = arena[parent_idx]
                    .children
                    .iter()
                    .any(|&c_idx| arena[c_idx].key == node_key);
                if is_duplicate {
                    integrity_violations.push(crate::models::IntegrityViolation {
                        check_name: "DUPLICATE-KEY".to_string(),
                        rule_id: "STR-001".to_string(),
                        message: format!(
                            "Structural Integrity: Duplicate key '{}' detected in the same block.",
                            node_key
                        ),
                        severity: "ERROR".to_string(),
                        line_no: shard.line_no,
                    });
                }
            }

            let node = ArenaNode {
                key: node_key,
                value: shard.value.clone(),
                children: Vec::new(),
                shards: vec![shard.clone()],
                indent: shard_indent,
                is_empty_flow: shard.is_flow_style
                    && shard
                        .value
                        .as_ref()
                        .map_or(false, |v| v == "[]" || v == "{}"),
            };

            // Collection Size Guardrail (prevents memory exhaustion on pathological files)
            if arena[parent_idx].children.len() < 5000 {
                let child_idx = arena.len();
                arena.push(node);
                arena[parent_idx].children.push(child_idx);

                if shard.value.is_none() || shard.is_list_item {
                    stack.push((shard_indent, child_idx));
                }
            }
        }
    }

    let root_node = convert_arena_to_semantic_node_owned(&mut arena, 0);

    SemanticManifest {
        root: root_node,
        indent_step: detected_step,
        integrity_violations,
    }
}

fn convert_arena_to_semantic_node_owned(arena: &mut [ArenaNode], idx: usize) -> SemanticNode {
    let node = std::mem::take(&mut arena[idx]);
    let children = node
        .children
        .iter()
        .map(|&c_idx| convert_arena_to_semantic_node_owned(arena, c_idx))
        .collect();

    SemanticNode {
        key: node.key,
        value: node.value,
        children,
        shards: node.shards,
        indent: node.indent,
        is_empty_flow: node.is_empty_flow,
    }
}

#[allow(dead_code)]
fn convert_arena_to_semantic_node(arena: &[ArenaNode], idx: usize) -> SemanticNode {
    let node = &arena[idx];
    let children = node
        .children
        .iter()
        .map(|&c_idx| convert_arena_to_semantic_node(arena, c_idx))
        .collect();

    SemanticNode {
        key: node.key.clone(),
        value: node.value.clone(),
        children,
        shards: node.shards.clone(),
        indent: node.indent,
        is_empty_flow: node.is_empty_flow,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_safe_structurize_basic() {
        let shards = vec![
            NativeShard {
                line_no: 1,
                indent: 0,
                key: "apiVersion".to_string(),
                value: Some("v1".to_string()),
                is_list_item: false,
                is_doc_boundary: false,
                is_block: false,
                is_flow_style: false,
                raw_line: "apiVersion: v1".to_string(),
                comment: String::new(),
                layout_sequence: Vec::new(),
                trailing_layout_sequence: Vec::new(),
                is_table_continuation: false,
                original_indent: 0,
                line_ending: "\n".to_string(),
            },
            NativeShard {
                line_no: 2,
                indent: 0,
                key: "kind".to_string(),
                value: Some("Pod".to_string()),
                is_list_item: false,
                is_doc_boundary: false,
                is_block: false,
                is_flow_style: false,
                raw_line: "kind: Pod".to_string(),
                comment: String::new(),
                layout_sequence: Vec::new(),
                trailing_layout_sequence: Vec::new(),
                is_table_continuation: false,
                original_indent: 0,
                line_ending: "\n".to_string(),
            },
        ];

        let manifest = native_structurize(shards);
        assert_eq!(manifest.root.children.len(), 2);
        assert_eq!(manifest.root.children[0].key, "apiVersion");
        assert_eq!(manifest.root.children[0].value.as_deref(), Some("v1"));
        assert_eq!(manifest.root.children[1].key, "kind");
        assert_eq!(manifest.root.children[1].value.as_deref(), Some("Pod"));
        assert!(manifest.integrity_violations.is_empty());
    }

    #[test]
    fn test_duplicate_key_detection() {
        let shards = vec![
            NativeShard {
                line_no: 1,
                indent: 0,
                key: "duplicate_key".to_string(),
                value: Some("first".to_string()),
                is_list_item: false,
                is_doc_boundary: false,
                is_block: false,
                is_flow_style: false,
                raw_line: "duplicate_key: first".to_string(),
                comment: String::new(),
                layout_sequence: Vec::new(),
                trailing_layout_sequence: Vec::new(),
                is_table_continuation: false,
                original_indent: 0,
                line_ending: "\n".to_string(),
            },
            NativeShard {
                line_no: 2,
                indent: 0,
                key: "duplicate_key".to_string(),
                value: Some("second".to_string()),
                is_list_item: false,
                is_doc_boundary: false,
                is_block: false,
                is_flow_style: false,
                raw_line: "duplicate_key: second".to_string(),
                comment: String::new(),
                layout_sequence: Vec::new(),
                trailing_layout_sequence: Vec::new(),
                is_table_continuation: false,
                original_indent: 0,
                line_ending: "\n".to_string(),
            },
        ];

        let manifest = native_structurize(shards);
        assert_eq!(manifest.integrity_violations.len(), 1);
        assert_eq!(manifest.integrity_violations[0].check_name, "DUPLICATE-KEY");
        assert_eq!(manifest.integrity_violations[0].line_no, 2);
    }

    #[test]
    fn test_deep_nesting_safe() {
        let mut shards = Vec::new();
        for i in 0..50 {
            shards.push(NativeShard {
                line_no: i + 1,
                indent: i * 2,
                key: format!("level_{}", i),
                value: if i == 49 {
                    Some("leaf".to_string())
                } else {
                    None
                },
                is_list_item: false,
                is_doc_boundary: false,
                is_block: false,
                is_flow_style: false,
                raw_line: format!("{}:", format!("level_{}", i)),
                comment: String::new(),
                layout_sequence: Vec::new(),
                trailing_layout_sequence: Vec::new(),
                is_table_continuation: false,
                original_indent: i * 2,
                line_ending: "\n".to_string(),
            });
        }

        let manifest = native_structurize(shards);
        let mut curr = &manifest.root;
        for i in 0..50 {
            assert_eq!(curr.children.len(), 1);
            assert_eq!(curr.children[0].key, format!("level_{}", i));
            curr = &curr.children[0];
        }
        assert_eq!(curr.value.as_deref(), Some("leaf"));
    }
}
