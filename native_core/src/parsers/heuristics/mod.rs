//! Lexical Physics Heuristics Engine
//!
//! Why: Coordinates the 12 discrete lexical and structural heuristics
//! ported from the legacy Yamlr engine to enforce the "Zero-Failure Trust Pillar"
//! and "Comment Preservation".

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

pub use boolean_guard::apply_boolean_guard;
pub use flow_sanitizer::apply_flow_sanitizer;
pub use indentation::{apply_snap_to_grid, apply_tab_expansion};
pub use keywords::{apply_keyword_fusion, apply_missing_colon};
pub use legacy::{identify_legacy_marker, LegacyMarkerType};
pub use list_indentation::apply_list_indentation;
pub use punctuation::{apply_magic_colon, apply_quote_balancing, apply_spacing};
pub use sequence::apply_fragmented_sequence;
pub use table_continuation::is_table_continuation_line;
pub use template_safety::{check_template_safety, TemplateSafetyStatus};

/// Pre-processes a raw manifest line through the active heuristic passes.
/// Pre-processes a raw manifest line through the active heuristic passes.
pub fn preprocess_line(
    raw_line: &str,
    next_line: Option<&str>,
    parent_indent: Option<usize>,
    in_block: bool,
) -> String {
    preprocess_line_with_grid(raw_line, next_line, parent_indent, in_block, false)
}

/// Pre-processes a raw manifest line with optional snap-to-grid indentation enforcement.
pub fn preprocess_line_with_grid(
    raw_line: &str,
    next_line: Option<&str>,
    parent_indent: Option<usize>,
    in_block: bool,
    snap_grid: bool,
) -> String {
    if in_block {
        return raw_line.to_string();
    }

    // 1. Template Safety Check
    let tpl_status = check_template_safety(raw_line);

    // 2. Tab expansion (standardize to spaces first)
    let line1 = apply_tab_expansion(raw_line);

    // 3. Flow style trailing comma cleanup
    let line2 = apply_flow_sanitizer(&line1, in_block);

    // 4. Fragmented sequence bullets (- - item, -- item)
    let line3 = apply_fragmented_sequence(&line2, in_block);

    // 5. Keyword fusion (kindService -> kind: Service)
    let line4 = apply_keyword_fusion(&line3, in_block);

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
    let line10 = apply_list_indentation(&line9, parent_indent, in_block);

    // 12. Snap odd indent to 2-space grid if requested
    if snap_grid {
        apply_snap_to_grid(&line10)
    } else {
        line10
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
}
