//! Table-Style Continuation Heuristic
//!
//! Why: In legacy manifests and ConfigMaps, multi-line list entries often break indentation
//! or lack subsequent `-` bullets on continuation rows. This heuristic identifies
//! continuation lines so they are bound as table continuations to the parent item.

/// Determines if a line is a table-style continuation of a preceding list item.
pub fn is_table_continuation_line(
    prev_is_list_item: bool,
    prev_indent: usize,
    current_indent: usize,
    current_is_list_item: bool,
    is_doc_boundary: bool,
) -> bool {
    if current_is_list_item || is_doc_boundary || !prev_is_list_item {
        return false;
    }

    // Previous was a list item, current has identical indent, but current lacks its own bullet.
    current_indent == prev_indent
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_identifies_continuation_row() {
        assert!(is_table_continuation_line(true, 4, 4, false, false));
        assert!(!is_table_continuation_line(false, 4, 4, false, false));
        assert!(!is_table_continuation_line(true, 4, 4, true, false));
        assert!(!is_table_continuation_line(true, 4, 2, false, false));
    }
}
