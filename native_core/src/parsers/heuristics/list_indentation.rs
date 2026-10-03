//! List Indentation Heuristic
//!
//! Why: In corrupted manifests or poorly formatted YAML, list items frequently appear
//! flush-left (`- item` at column 0 under an indented parent like `containers:`) or with
//! odd-spaced floating indentation (3, 5, 7 spaces). This heuristic realigns list hyphens
//! relative to their parent context.

/// Normalizes list item indentation relative to the parent mapping indent.
pub fn apply_list_indentation(line: &str, parent_indent: Option<usize>, in_block: bool) -> String {
    if in_block {
        return line.to_string();
    }

    let stripped = line.trim_start();
    if !stripped.starts_with('-') || stripped.starts_with("---") {
        return line.to_string();
    }

    let current_indent = line.len() - stripped.len();

    if let Some(parent) = parent_indent {
        // 1. Flush-Left Recovery: "- item" at 0 while parent is indented
        if current_indent == 0 && parent > 0 {
            let expected_indent = parent + 2;
            let mut out = String::with_capacity(expected_indent + stripped.len());
            out.push_str(&" ".repeat(expected_indent));
            out.push_str(stripped);
            return out;
        }

        // 2. Grid Misalignment: Odd-numbered indentations (3, 5, 7 spaces)
        if current_indent > 0 && current_indent % 2 != 0 {
            let expected_indent = parent + 2;
            let final_indent = if (current_indent as isize - expected_indent as isize).abs() <= 1 {
                expected_indent
            } else {
                current_indent + 1 // Round up to even
            };

            let mut out = String::with_capacity(final_indent + stripped.len());
            out.push_str(&" ".repeat(final_indent));
            out.push_str(stripped);
            return out;
        }
    }

    line.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_flush_left_recovery() {
        let parent_indent = Some(2); // e.g. "  containers:"
        let line = "- name: web";
        assert_eq!(
            apply_list_indentation(line, parent_indent, false),
            "    - name: web"
        );
    }

    #[test]
    fn test_snaps_odd_list_indent() {
        let parent_indent = Some(2); // "  containers:"
        let line = "   - name: web"; // indent 3
        assert_eq!(
            apply_list_indentation(line, parent_indent, false),
            "    - name: web"
        );
    }
}
