use crate::models::NativeShard;
use std::collections::HashMap;

pub use crate::parsers::layout_grafter::{
    native_apply_heuristics, native_apply_layout_grafter, LayoutGrafter,
};
pub use crate::parsers::streaming::{
    native_shard_stream, stream_document_slices, NativeDocumentSliceStream, NativeShardStream,
};

pub fn native_strip_bom(content: &str) -> &str {
    content.strip_prefix("\u{feff}").unwrap_or(content)
}

pub fn native_find_comment_split(text: &str) -> i32 {
    let mut in_double_quote = false;
    let mut in_single_quote = false;
    let mut escaped = false;

    for (i, c) in text.chars().enumerate() {
        if escaped {
            escaped = false;
            continue;
        }
        if c == '\\' {
            escaped = true;
            continue;
        }
        if c == '"' && !in_single_quote {
            in_double_quote = !in_double_quote;
        } else if c == '\'' && !in_double_quote {
            in_single_quote = !in_single_quote;
        }

        if c == '#' && !in_double_quote && !in_single_quote {
            if i == 0 || text.as_bytes()[i - 1].is_ascii_whitespace() {
                return i as i32;
            }
        }
    }
    -1
}

pub fn native_shard(content: &str) -> Vec<NativeShard> {
    // Manifest Size Guardrail
    if content.len() > 10 * 1024 * 1024 {
        return vec![NativeShard {
            line_no: 0,
            indent: 0,
            key: "Error".to_string(),
            value: Some("Security Violation: Manifest size exceeds 10MB limit.".to_string()),
            is_list_item: false,
            is_doc_boundary: false,
            is_block: false,
            is_flow_style: false,
            raw_line: "# [Yamlr:S-001] Manifest Size Violation".to_string(),
            comment: String::new(),
            layout_sequence: Vec::new(),
            trailing_layout_sequence: Vec::new(),
            is_table_continuation: false,
            original_indent: 0,
            line_ending: "\n".to_string(),
        }];
    }
    // Binary File Guardrail
    // If the content contains NULL bytes, it's almost certainly binary.
    // We abort to prevent memory spikes and garbage processing.
    if content.chars().any(|c| c == '\0') {
        return Vec::new();
    }

    let stripped = native_strip_bom(content);
    let mut content_clean = String::with_capacity(stripped.len());
    for c in stripped.chars() {
        if c.is_control() && c != '\n' && c != '\r' && c != '\t' {
            continue;
        }
        match c {
            '\u{00A0}' => content_clean.push(' '),
            '\u{200B}' | '\u{200C}' | '\u{200D}' => {}
            '\u{201C}' | '\u{201D}' => content_clean.push('"'),
            '\u{2018}' | '\u{2019}' => content_clean.push('\''),
            _ => content_clean.push(c),
        }
    }

    let mut doc_count = 1;
    let mut is_inside_block = false;
    let mut block_indent = 0;

    let mut key_registry: HashMap<usize, Vec<String>> = HashMap::new();
    let mut current_indent = 0;
    let mut layout_buffer: Vec<String> = Vec::new();

    // Split by \n but track if it was preceded by \r
    let lines: Vec<&str> = content_clean.split('\n').collect();
    let mut shards = Vec::with_capacity(lines.len());

    for (i, line_raw) in lines.iter().enumerate() {
        let (line, line_ending) = if line_raw.ends_with('\r') {
            (&line_raw[..line_raw.len() - 1], "\r\n")
        } else {
            (*line_raw, "\n")
        };

        // Shard Stability Guardrail
        if shards.len() >= 100000 {
            break;
        }

        // Context-Fidelity Normalization
        let mut indent_part = "";
        let mut code_start = line.len();
        for (idx, c) in line.char_indices() {
            if c != ' ' && c != '\t' {
                indent_part = &line[..idx];
                code_start = idx;
                break;
            }
        }
        let line_normalized = if code_start < line.len() {
            format!("{}{}", indent_part.replace("\t", "  "), &line[code_start..])
        } else {
            line.replace("\t", "  ") // Entirely whitespace
        };

        let trimmed_start = line_normalized.trim_start();
        let indent = line_normalized.len() - trimmed_start.len();
        if line.trim().is_empty() {
            if is_inside_block {
                shards.push(NativeShard {
                    line_no: i + 1,
                    indent: block_indent + 2,
                    key: String::new(),
                    value: Some(String::new()),
                    is_list_item: false,
                    is_doc_boundary: false,
                    is_block: false,
                    is_flow_style: false,
                    raw_line: line_raw.to_string(), // Preserve raw including \r
                    comment: String::new(),
                    layout_sequence: Vec::new(),
                    trailing_layout_sequence: Vec::new(),
                    is_table_continuation: true,
                    original_indent: 0,
                    line_ending: line_ending.to_string(),
                });
            } else {
                layout_buffer.push(line_raw.to_string()); // Preserve raw including \r
            }
            continue;
        }

        // Comment Isolation (Early)
        let comment_idx = native_find_comment_split(&line_normalized);
        let (code_part, mut comment) = if comment_idx != -1 {
            (
                line_normalized[..comment_idx as usize].trim(),
                line_normalized[comment_idx as usize..].to_string(),
            )
        } else {
            (line_normalized.trim(), String::new())
        };

        // Comment Length Guardrail
        if comment.len() > 8192 {
            comment = comment[..8192].to_string();
        }

        // Pure Comment Preservation
        if code_part.is_empty() && !comment.is_empty() {
            shards.push(NativeShard {
                line_no: i + 1,
                indent,
                key: String::new(),
                value: None,
                is_list_item: false,
                is_doc_boundary: false,
                is_block: false,
                is_flow_style: false,
                raw_line: line_raw.to_string(), // Preserve raw including \r
                comment,
                layout_sequence: Vec::new(),
                trailing_layout_sequence: Vec::new(),
                is_table_continuation: false,
                original_indent: indent,
                line_ending: line_ending.to_string(),
            });
            continue;
        }

        // Manage key registry for duplicate detection
        if indent <= current_indent {
            key_registry.retain(|&k, _| k <= indent);
        }
        current_indent = indent;

        // [Rest of block logic...]
        if is_inside_block {
            if indent > block_indent || code_part.is_empty() {
                shards.push(NativeShard {
                    line_no: i + 1,
                    indent,
                    key: String::new(),
                    value: Some(code_part.to_string()),
                    is_list_item: false,
                    is_doc_boundary: false,
                    is_block: false,
                    is_flow_style: false,
                    raw_line: line_raw.to_string(),
                    comment,
                    layout_sequence: Vec::new(),
                    trailing_layout_sequence: Vec::new(),
                    is_table_continuation: true,
                    original_indent: indent,
                    line_ending: line_ending.to_string(),
                });
                continue;
            } else {
                is_inside_block = false;
            }
        }

        // Lexical Physics Heuristics Pass
        let next_line_peek = lines.get(i + 1).copied();
        let healed_code_part = if !is_inside_block && !code_part.is_empty() {
            crate::parsers::heuristics::preprocess_line(code_part, next_line_peek, None, false)
        } else {
            code_part.to_string()
        };
        let code_part = &healed_code_part;

        // Fuzzy Boundary Detection
        let is_doc_boundary =
            indent == 0 && !code_part.is_empty() && code_part.chars().all(|c| c == '-');
        let is_doc_end = code_part == "...";

        // Indentation-Indicator-Aware Sharding
        let is_block = {
            let cp = code_part.trim_end();
            cp.ends_with('|') || cp.ends_with('>') ||
            // Handle indicators like |2, |+, |-, |+2, |2+, etc.
            (cp.len() >= 2 && (cp.chars().nth(cp.len()-2) == Some('|') || cp.chars().nth(cp.len()-2) == Some('>')) &&
             (cp.chars().last().unwrap().is_ascii_digit() || cp.chars().last().unwrap() == '+' || cp.chars().last().unwrap() == '-')) ||
            (cp.len() >= 3 && (cp.chars().nth(cp.len()-3) == Some('|') || cp.chars().nth(cp.len()-3) == Some('>')) &&
             (cp.chars().last().unwrap().is_ascii_digit() || cp.chars().last().unwrap() == '+' || cp.chars().last().unwrap() == '-'))
        };

        let is_flow_style = code_part.starts_with('{') || code_part.starts_with('[');

        // Flow-Style Quarantine
        // If a flow-style block is unclosed on a single line, auto-close it
        // to prevent 'Nuclear Errors' in the parser.
        let mut final_code_part = code_part.to_string();
        if is_flow_style {
            if final_code_part.starts_with('{') && !final_code_part.contains('}') {
                final_code_part.push('}');
            } else if final_code_part.starts_with('[') && !final_code_part.contains(']') {
                final_code_part.push(']');
            }
        }
        let code_part = &final_code_part;

        if is_doc_boundary || is_doc_end {
            // Document Stability Guardrail
            if doc_count >= 1000 {
                continue; // Stop processing new documents
            }
            doc_count += 1;

            is_inside_block = false;
            key_registry.clear();
            shards.push(NativeShard {
                line_no: i + 1,
                indent: 0,
                key: String::new(),
                value: None,
                is_list_item: false,
                is_doc_boundary: true,
                is_block: false,
                is_flow_style: false,
                raw_line: line_raw.to_string(), // Preserve raw including \r
                comment,
                layout_sequence: Vec::new(),
                trailing_layout_sequence: Vec::new(),
                is_table_continuation: false,
                original_indent: 0,
                line_ending: line_ending.to_string(),
            });
            continue;
        }

        if is_block {
            is_inside_block = true;
            block_indent = indent;
        }

        let mut key = String::new();
        let mut value = None;

        // List-Typo Recovery
        // Recognizes '-name: pod' as a list item '- name: pod'
        let is_list_item = code_part.starts_with("- ");
        let is_list_typo = code_part.starts_with("-")
            && code_part.len() > 1
            && code_part.chars().nth(1).unwrap() != ' ';

        let final_is_list_item = is_list_item || is_list_typo;

        let data_part = if is_list_item {
            if code_part.len() > 2 {
                &code_part[2..]
            } else {
                ""
            }
        } else if is_list_typo {
            &code_part[1..]
        } else {
            code_part
        };

        let mut final_indent = indent;
        if !shards.is_empty() {
            let prev = &shards[shards.len() - 1];
            if !prev.key.is_empty() && prev.value.is_none() && is_list_item && indent == 0 {
                final_indent = prev.indent + 2;
            }
        }

        let has_colon = data_part.contains(':');

        // Zero-Loss Integrity
        // We NO LONGER skip lines without colons. We preserve them as 'unstructured' shards.
        if !has_colon && !is_list_item {
            shards.push(NativeShard {
                line_no: i + 1,
                indent: final_indent,
                key: String::new(),
                value: Some(data_part.to_string()),
                is_list_item: false,
                is_doc_boundary: false,
                is_block: false,
                is_flow_style: false,
                raw_line: line_raw.to_string(), // Preserve raw including \r
                comment,
                layout_sequence: Vec::new(),
                trailing_layout_sequence: Vec::new(),
                is_table_continuation: true,
                original_indent: indent,
                line_ending: line_ending.to_string(),
            });
            continue;
        }

        // Strict Semantic Separation
        let split_pos = if data_part.starts_with('"') || data_part.starts_with('\'') {
            let quote_char = data_part.chars().next().unwrap();
            let is_double_quote = quote_char == '"';

            // Quote-Semantic-Aware Sharding
            let mut escaped = false;
            let mut end_quote_pos = None;
            for (i, c) in data_part.char_indices().skip(1) {
                if is_double_quote && escaped {
                    escaped = false;
                    continue;
                }
                if is_double_quote && c == '\\' {
                    escaped = true;
                    continue;
                }
                // Single Quote special escape: ''
                if !is_double_quote && c == '\'' && data_part.chars().nth(i + 1) == Some('\'') {
                    // This is an escaped single quote, skip next char too
                    continue; // Skip first quote, loop will handle second
                }
                if c == quote_char {
                    end_quote_pos = Some(i);
                    break;
                }
            }

            if let Some(pos) = end_quote_pos {
                let after_quote = &data_part[pos + 1..];
                after_quote.find(':').map(|p| p + pos + 1)
            } else {
                data_part.find(':')
            }
        } else {
            // Unquoted colon must be followed by space or end of line
            data_part
                .char_indices()
                .find(|(i, c)| {
                    *c == ':' && (data_part.len() == i + 1 || data_part[i + 1..].starts_with(' '))
                })
                .map(|(i, _)| i)
        };

        if let Some(pos) = split_pos {
            let mut raw_key = data_part[..pos].trim_end();

            // Key Length Guardrail
            if raw_key.len() > 2048 {
                raw_key = &raw_key[..2048];
            }

            let clean_key = raw_key.trim_matches(|c| c == '"' || c == '\'');
            key = crate::parsers::interner::intern_k8s_key(clean_key)
                .map(|s| s.to_string())
                .unwrap_or_else(|| clean_key.to_string());

            // Bad-Merge Recovery
            // If we see a root-level identity key (kind/apiVersion) that we've already
            // seen in this document, it's a 'Bad Merge'. Inject a virtual boundary.
            if !final_is_list_item && final_indent == 0 && (key == "kind" || key == "apiVersion") {
                let keys_at_root = key_registry
                    .entry(0)
                    .or_insert_with(|| Vec::<String>::new());
                if keys_at_root.contains(&key) {
                    // INJECT VIRTUAL BOUNDARY
                    shards.push(NativeShard {
                        line_no: i + 1,
                        indent: 0,
                        key: String::new(),
                        value: None,
                        is_list_item: false,
                        is_doc_boundary: true,
                        is_block: false,
                        is_flow_style: false,
                        raw_line: "--- # [Yamlr] Auto-Injected Boundary (Bad Merge Recovery)"
                            .to_string(),
                        comment: String::new(),
                        layout_sequence: Vec::new(),
                        trailing_layout_sequence: Vec::new(),
                        is_table_continuation: false,
                        original_indent: 0,
                        line_ending: line_ending.to_string(),
                    });
                    keys_at_root.clear();
                }
            }

            // Case-Fuzzy Collision Protection
            if !key.is_empty() {
                let keys_at_indent = key_registry
                    .entry(indent)
                    .or_insert_with(|| Vec::<String>::new());
                let normalized_key = key.to_lowercase();

                // We only perform Case-Fuzzy detection for core identity fields
                // to avoid disrupting valid case-sensitive user data in ConfigMaps.
                let is_identity_field = normalized_key == "kind" || normalized_key == "apiversion";

                if is_identity_field {
                    if keys_at_indent
                        .iter()
                        .any(|k| k.to_lowercase() == normalized_key)
                    {
                        // Collision detected! (Handled in Bad-Merge Recovery)
                    } else {
                        keys_at_indent.push(key.clone());
                    }
                } else {
                    if keys_at_indent.contains(&key) {
                        // Exact match duplicate
                    } else {
                        keys_at_indent.push(key.clone());
                    }
                }
            }

            let mut val_part = data_part[pos + 1..].trim();

            // Value Length Guardrail
            if val_part.len() > 65536 {
                val_part = &val_part[..65536];
            }

            if !val_part.is_empty() {
                let clean_val_comment_idx = native_find_comment_split(val_part);
                let mut clean_val = if clean_val_comment_idx != -1 {
                    val_part[..clean_val_comment_idx as usize].trim()
                } else {
                    val_part
                }
                .to_string();

                // Null-Safe Value Sanitization
                if clean_val.contains('\0') {
                    clean_val = clean_val.replace('\0', " [NULL] ");
                }

                // Clean-Stream Sanitization
                clean_val = clean_val
                    .chars()
                    .map(|c| {
                        if c.is_control() && c != '\t' && c != '\n' && c != '\r' {
                            ' '
                        } else {
                            c
                        }
                    })
                    .collect();

                // Quote Auto-Balancing
                if clean_val.len() > 1 {
                    let first = clean_val.chars().next().unwrap();
                    let last = clean_val.chars().last().unwrap();
                    if (first == '"' || first == '\'') && last != first {
                        clean_val.push(first);
                    }
                }
                if !clean_val.is_empty() {
                    value = Some(clean_val.to_string());
                }
            }
        } else if final_is_list_item {
            let clean_val = data_part.trim();
            if !clean_val.is_empty() {
                value = Some(clean_val.to_string());
            }
        }

        shards.push(NativeShard {
            line_no: i + 1,
            indent: final_indent,
            key,
            value,
            is_list_item: final_is_list_item,
            is_doc_boundary: false,
            is_block,
            is_flow_style,
            raw_line: line_raw.to_string(), // Preserve raw including \r
            comment,
            layout_sequence: Vec::new(),
            trailing_layout_sequence: Vec::new(),
            is_table_continuation: !data_part.trim().is_empty()
                && !has_colon
                && !final_is_list_item,
            original_indent: indent,
            line_ending: line_ending.to_string(),
        });
    }
    // Total EOF Preservation
    if !layout_buffer.is_empty() && !shards.is_empty() {
        let last_idx = shards.len() - 1;
        shards[last_idx]
            .trailing_layout_sequence
            .extend(layout_buffer);
    }

    shards
}

pub use crate::parsers::layout_grafter::native_apply_shadow;
pub use crate::parsers::reconstructor::native_reconstruct_yaml;
pub use crate::parsers::shard_finder::{
    native_find_shard_by_path, native_shard_doc_chunks as native_shard_doc_chunks_from_shards,
};

/// Splits raw manifest content into document chunks separated by `---`.
pub fn native_shard_doc_chunks(content: &str) -> Vec<Vec<NativeShard>> {
    let shards = native_shard(content);
    native_shard_doc_chunks_from_shards(&shards)
}

#[cfg(test)]
#[path = "sharder_tests.rs"]
mod tests;
