//! Lexical Physics Heuristics Engine
//!
//! Why: Coordinates the 12 discrete lexical and structural heuristics
//! ported from the legacy Yamlr engine to enforce the "Zero-Failure Trust Pillar"
//! and "Comment Preservation".

pub mod block_scalar_indentation;
pub mod boolean_guard;
pub mod flow_sanitizer;
pub mod indentation;
pub mod keywords;
pub mod legacy;
pub mod list_indentation;
pub mod punctuation;
pub mod sequence;
pub mod table_continuation;
pub mod template_safety;

pub use block_scalar_indentation::{heal_unindented_block_line, is_block_scalar_header, RULE_SYN_015};
pub use boolean_guard::apply_boolean_guard;
pub use flow_sanitizer::apply_flow_sanitizer;
pub use indentation::{apply_dangling_child_indentation, apply_snap_to_grid, apply_tab_expansion};
pub use keywords::{apply_keyword_fusion, apply_missing_colon};
pub use legacy::{identify_legacy_marker, LegacyMarkerType};
pub use list_indentation::apply_list_indentation;
pub use punctuation::{apply_magic_colon, apply_quote_balancing, apply_spacing};
pub use sequence::{apply_env_key_value_sequence, apply_fragmented_sequence};
pub use table_continuation::is_table_continuation_line;
pub use template_safety::{check_template_safety, normalize_template_braces, TemplateSafetyStatus};

/// Pre-processes a raw manifest line through the active heuristic passes.
/// Pre-processes a raw manifest line through the active heuristic passes.
pub fn preprocess_line(
    raw_line: &str,
    next_line: Option<&str>,
    parent_indent: Option<usize>,
    in_block: bool,
) -> String {
    preprocess_line_with_context(raw_line, next_line, 0, None, parent_indent, in_block, false)
}

/// Pre-processes a raw manifest line with optional snap-to-grid indentation enforcement.
pub fn preprocess_line_with_grid(
    raw_line: &str,
    next_line: Option<&str>,
    parent_indent: Option<usize>,
    in_block: bool,
    snap_grid: bool,
) -> String {
    preprocess_line_with_context(raw_line, next_line, 0, None, parent_indent, in_block, snap_grid)
}

/// Pre-processes a raw manifest line with parent key and indentation context.
pub fn preprocess_line_with_context(
    raw_line: &str,
    next_line: Option<&str>,
    line_indent: usize,
    parent_key: Option<&str>,
    parent_indent: Option<usize>,
    in_block: bool,
    snap_grid: bool,
) -> String {
    if in_block {
        return raw_line.to_string();
    }

    // 1. Template Brace Normalization (Trap 36: `{{{{` -> `{{`)
    let line0 = normalize_template_braces(raw_line);

    // 1b. Template Safety Check
    let tpl_status = check_template_safety(&line0);

    // 2. Tab expansion (standardize to spaces first)
    let line1 = apply_tab_expansion(&line0);

    // 3. Flow style trailing comma cleanup
    let line2 = apply_flow_sanitizer(&line1, in_block);

    // 4. Fragmented sequence bullets (- - item, -- item)
    let line3 = apply_fragmented_sequence(&line2, in_block);

    // 4b. Docker Compose / .env key-value syntax under env: sequences (- KEY=VAL -> - name: KEY\n  value: "VAL")
    let line3b = apply_env_key_value_sequence(&line3, parent_key, in_block);

    // 5. Keyword fusion (kindService -> kind: Service)
    let line4 = apply_keyword_fusion(&line3b, in_block);

    // 6. Missing colon lookahead
    let line5 = apply_missing_colon(&line4, next_line, in_block);

    // 7. Spacing around markers (-item -> - item, key:value -> key: value)
    let line6 = apply_spacing(&line5, tpl_status.skip_punctuation_healing);

    // 8. Magic colon injection (image nginx -> image: nginx)
    let line7 = apply_magic_colon(&line6, tpl_status.skip_punctuation_healing);

    // 9. Quote balancing
    let line8 = apply_quote_balancing(&line7, tpl_status.skip_punctuation_healing);

    // 10. Boolean guard (Norway problem: unquoted yes/no -> "yes"/"no")
    let line9 = apply_boolean_guard(&line8, in_block);

    // 11. List indentation normalization
    let line10 = apply_list_indentation(&line9, line_indent, parent_indent, in_block);

    // 12. Dangling zero-indent child key under parent mapping (e.g. metadata:\nname: web)
    let line11 = apply_dangling_child_indentation(&line10, line_indent, parent_key, parent_indent, in_block);

    // 13. Snap odd indent to 2-space grid if requested
    if snap_grid {
        apply_snap_to_grid(&line11)
    } else {
        line11
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_combined_preprocessing() {
        // Tab + boolean + missing space
        let raw = "\tenabled:yes";
        let processed = preprocess_line(raw, None, None, false);
        assert_eq!(processed, "  enabled: \"yes\"");

        // Fused keyword
        let fused = "kindService";
        let processed_fused = preprocess_line(fused, None, None, false);
        assert_eq!(processed_fused, "kind: Service");
    }

    #[test]
    fn test_phase_4_comprehensive_idempotency_and_human_typos() {
        let test_cases = vec![
            // 1. Scalar Header Typos
            ("description: >>", "description: >"),
            ("script: ||", "script: |"),
            // Negative check: shell redirects inside scripts must NOT be altered
            ("  echo 'data' >> /tmp/log", "  echo 'data' >> /tmp/log"),

            // 2. Key Semicolons & Multiple Colons
            ("metadata;", "metadata:"),
            ("  spec;", "  spec:"),
            ("metadata::", "metadata:"),
            ("annotations :", "annotations:"),

            // 3. Flow Collection Bracket Asymmetry & Pair Matching
            ("env: [[ name: APP_ENV, value: prod }]", "env: [{ name: APP_ENV, value: prod }]"),
            ("env: [{ name: APP_ENV, value: prod }}]", "env: [{ name: APP_ENV, value: prod }]"),
            ("ports: [80, 443}", "ports: [80, 443]"),
            ("ports: [80, 443, ]", "ports: [80, 443]"),

            // 4. Quote Syntax & Nested Escapes
            ("- \"-c'", "- \"-c\""),
            ("tag: \"\"\"v1.2.3\"\"\"", "tag: \"v1.2.3\""),
            ("- \"echo \"starting server...\" && exec\"", "- \"echo 'starting server...' && exec\""),
            ("image: \"nginx:latest", "image: \"nginx:latest\""),
        ];

        for (input, expected) in test_cases {
            let healed_once = preprocess_line(input, None, None, false);
            assert_eq!(
                healed_once, expected,
                "Failed on input '{}': expected '{}', got '{}'",
                input, expected, healed_once
            );

            // Phase 4 Idempotency Guarantee: h(h(x)) == h(x)
            let healed_twice = preprocess_line(&healed_once, None, None, false);
            assert_eq!(
                healed_twice, healed_once,
                "Idempotency violation on '{}': second pass produced '{}'",
                healed_once, healed_twice
            );
        }
    }
}
