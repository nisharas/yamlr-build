//! AST String Reconstruction and Layout-Preserving Serializer.
//!
//! Why: Reconstructs YAML manifest text from the SemanticManifest arena tree,
//! preserving original comments, odd-space indentations, chomping block scalars,
//! and empty flow styles without memory corruption or data loss.

use crate::models::{NativeShard, SemanticManifest, SemanticNode};

fn native_quote_if_reserved(val: &str) -> String {
    let reserved = [
        "y", "Y", "yes", "Yes", "YES", "n", "N", "no", "No", "NO", "on", "On", "ON", "off", "Off",
        "OFF", "null", "Null", "NULL", "~",
    ];
    if reserved.contains(&val) {
        format!("\"{}\"", val)
    } else {
        val.to_string()
    }
}

fn native_quote_key_if_required(key: &str) -> String {
    if !key.contains(':') {
        return key.to_string();
    }

    format!("\"{}\"", key.replace('\\', "\\\\").replace('"', "\\\""))
}

/// Reconstructs a formatted YAML string from raw native shards.
pub fn native_reconstruct_yaml(shards: &[NativeShard]) -> String {
    let mut out = Vec::new();
    for s in shards {
        for layout in &s.layout_sequence {
            out.push(layout.clone());
        }

        let mut line = String::new();
        line.push_str(&" ".repeat(s.indent));

        if s.is_doc_boundary {
            line.push_str("---");
        } else if s.is_table_continuation {
            if let Some(val) = &s.value {
                line.push_str(val);
            }
        } else {
            if s.is_list_item {
                line.push_str("- ");
            }
            if !s.key.is_empty() {
                line.push_str(&native_quote_key_if_required(&s.key));
                line.push_str(":");
                if let Some(val) = &s.value {
                    if !val.is_empty() {
                        line.push_str(" ");
                    }
                }
            }
            if let Some(val) = &s.value {
                line.push_str(&native_quote_if_reserved(val));
            }
        }

        if !s.comment.is_empty() {
            if !line.trim().is_empty() {
                line.push_str(" ");
            }
            line.push_str(&s.comment);
        }

        out.push(line);

        for layout in &s.trailing_layout_sequence {
            out.push(layout.clone());
        }
    }
    out.join("\n")
}

/// Reconstructs a formatted YAML string from a SemanticManifest.
pub fn native_reconstruct_from_semantic(manifest: &SemanticManifest) -> String {
    let mut output = String::new();
    reconstruct_node(&manifest.root, &mut output, 0);

    if semantic_contains_crlf(&manifest.root) {
        output = output.replace("\r\n", "\n").replace('\n', "\r\n");
    }

    // Trailing Layout Preservation
    // Pull the final blank lines/whitespace from the root's trailing DNA
    if let Some(shard) = manifest.root.shards.last() {
        for layout in &shard.trailing_layout_sequence {
            output.push_str(layout);
            output.push('\n');
        }
    }

    output
}

fn semantic_contains_crlf(node: &SemanticNode) -> bool {
    node.shards.iter().any(|shard| shard.line_ending == "\r\n")
        || node.children.iter().any(semantic_contains_crlf)
}

/// Recursively formats a semantic node into the output YAML string.
pub fn reconstruct_node(node: &SemanticNode, output: &mut String, depth: usize) {
    if depth > 255 {
        return; // SAFETY: Stack Overflow Protection
    }

    for child in &node.children {
        let prefix = " ".repeat(child.indent);

        // Comment Grafting & List Awareness
        let mut is_list = false;
        let comment_str = if let Some(shard) = child.shards.first() {
            is_list = shard.is_list_item;
            if !shard.comment.is_empty() {
                format!(" {}", shard.comment)
            } else {
                "".to_string()
            }
        } else {
            "".to_string()
        };

        let list_prefix = if is_list { "- " } else { "" };
        let final_prefix = if is_list {
            if let Some(shard) = child.shards.first() {
                " ".repeat(shard.original_indent)
            } else {
                prefix.clone()
            }
        } else {
            prefix.clone()
        };

        if child.key == "-" && child.value.is_none() {
            if let Some((first, rest)) = child.children.split_first() {
                // First element rendered with "- " list prefix
                let first_indent_spaces = " ".repeat(child.indent);
                let first_comment = if let Some(shard) = first.shards.first() {
                    if !shard.comment.is_empty() {
                        format!(" {}", shard.comment)
                    } else {
                        "".to_string()
                    }
                } else {
                    "".to_string()
                };

                if let Some(f_val) = &first.value {
                    output.push_str(&format!(
                        "{}- {}: {}{}\n",
                        first_indent_spaces,
                        native_quote_key_if_required(&first.key),
                        f_val,
                        first_comment
                    ));
                } else {
                    output.push_str(&format!(
                        "{}- {}:{}\n",
                        first_indent_spaces,
                        native_quote_key_if_required(&first.key),
                        first_comment
                    ));
                }
                reconstruct_node(first, output, depth + 1);

                // Subsequent elements at child.indent + 2
                let rest_indent_spaces = " ".repeat(child.indent + 2);
                for rest_child in rest {
                    let rest_comment = if let Some(shard) = rest_child.shards.first() {
                        if !shard.comment.is_empty() {
                            format!(" {}", shard.comment)
                        } else {
                            "".to_string()
                        }
                    } else {
                        "".to_string()
                    };

                    if let Some(r_val) = &rest_child.value {
                        output.push_str(&format!(
                            "{}{}: {}{}\n",
                            rest_indent_spaces,
                            native_quote_key_if_required(&rest_child.key),
                            r_val,
                            rest_comment
                        ));
                    } else {
                        output.push_str(&format!(
                            "{}{}:{}\n",
                            rest_indent_spaces,
                            native_quote_key_if_required(&rest_child.key),
                            rest_comment
                        ));
                    }
                    reconstruct_node(rest_child, output, depth + 1);
                }
            } else {
                let first_indent_spaces = " ".repeat(child.indent);
                output.push_str(&format!("{}-\n", first_indent_spaces));
            }
            continue;
        }

        if let Some(val) = &child.value {
            if child.key == "-" {
                output.push_str(&format!(
                    "{}{}{}{}\n",
                    final_prefix, list_prefix, val, comment_str
                ));
            } else {
                output.push_str(&format!(
                    "{}{}{}: {}{}\n",
                    final_prefix,
                    list_prefix,
                    native_quote_key_if_required(&child.key),
                    val,
                    comment_str
                ));
            }

            // RENDER CONTINUATION SHARDS (Multiline Strings)
            for shard in child.shards.iter().skip(1) {
                if shard.is_table_continuation {
                    output.push_str(&format!("{}\n", shard.raw_line));
                }
            }

            if !child.children.is_empty() {
                reconstruct_node(child, output, depth + 1);
            }
        } else {
            if child.is_empty_flow {
                // RECOVER ORIGINAL EMPTY FLOW STYLE
                let flow_val = if child
                    .shards
                    .first()
                    .map_or(false, |s| s.raw_line.contains("{}"))
                {
                    "{}"
                } else {
                    "[]"
                };
                output.push_str(&format!(
                    "{}{}{}: {}{}\n",
                    final_prefix,
                    list_prefix,
                    native_quote_key_if_required(&child.key),
                    flow_val,
                    comment_str
                ));
            } else {
                if child.key == "-" {
                    output.push_str(&format!("{}{}{}\n", final_prefix, list_prefix, comment_str));
                } else if child.key.is_empty() {
                    let raw = child
                        .shards
                        .first()
                        .map(|s| s.raw_line.as_str())
                        .unwrap_or(comment_str.trim_start());
                    output.push_str(&format!("{}\n", raw));
                } else {
                    output.push_str(&format!(
                        "{}{}{}:{}\n",
                        final_prefix,
                        list_prefix,
                        native_quote_key_if_required(&child.key),
                        comment_str
                    ));
                }

                // RENDER CONTINUATION SHARDS (Multiline Strings)
                for shard in child.shards.iter().skip(1) {
                    if shard.is_table_continuation {
                        output.push_str(&format!("{}\n", shard.raw_line));
                    }
                }

                reconstruct_node(child, output, depth + 1);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_reconstruct_basic_manifest() {
        let input = "apiVersion: v1\nkind: Service\nmetadata:\n  name: my-svc\n";
        let shards = native_shard(input);
        let manifest = native_structurize(shards);
        let reconstructed = native_reconstruct_from_semantic(&manifest);
        assert!(reconstructed.contains("apiVersion: v1"));
        assert!(reconstructed.contains("kind: Service"));
        assert!(reconstructed.contains("name: my-svc"));
    }

    #[test]
    fn test_reconstruct_with_comments() {
        let input = "apiVersion: v1\n# Service kind comment\nkind: Service\nmetadata:\n  name: my-svc # Inline comment\n";
        let shards = native_shard(input);
        let manifest = native_structurize(shards);
        let reconstructed = native_reconstruct_from_semantic(&manifest);
        assert!(reconstructed.contains("Inline comment"));
    }
}
