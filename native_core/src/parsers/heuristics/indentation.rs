//! Indentation Heuristics: Tab Expansion & Snap to Grid
//!
//! Why: Kubernetes manifests follow a strict 2-space indentation standard.
//! Hard tabs (`\t`) break standard YAML parsers, while odd-numbered indentation levels
//! (1, 3, 5 spaces) create structural ambiguity across parent/child nodes.
//! These heuristics normalize indentation to a strict 2-space grid.

/// Expands literal tab characters into 2 spaces.
pub fn apply_tab_expansion(line: &str) -> String {
    if !line.contains('\t') {
        return line.to_string();
    }
    line.replace('\t', "  ")
}

/// Snaps odd-numbered indentations to the nearest even 2-space grid point.
pub fn apply_snap_to_grid(line: &str) -> String {
    let raw_line = line.trim_end();
    let content = raw_line.trim_start();
    let indent = raw_line.len() - content.len();

    if content.is_empty() {
        return line.to_string();
    }

    if indent > 0 && indent % 2 != 0 {
        let new_indent = if indent == 1 { 2 } else { indent - 1 };

        let mut out = String::with_capacity(new_indent + content.len());
        out.push_str(&" ".repeat(new_indent));
        out.push_str(content);
        out
    } else {
        line.to_string()
    }
}

/// Known standard child keys under K8s parent sections like `metadata:`.
/// When an author writes `metadata:\nname: web` with 0 indentation, this heuristic
/// safely indents `name:` under `metadata:`.
const KNOWN_METADATA_CHILD_KEYS: &[&str] = &[
    "name",
    "namespace",
    "labels",
    "annotations",
    "generateName",
    "ownerReferences",
    "finalizers",
];

/// Indents dangling child keys that immediately follow an empty parent mapping header.
pub fn apply_dangling_child_indentation(
    line: &str,
    line_indent: usize,
    parent_key: Option<&str>,
    parent_indent: Option<usize>,
    in_block: bool,
) -> String {
    if in_block {
        return line.to_string();
    }

    let stripped = line.trim_start();

    if let (Some(parent), Some(p_indent)) = (parent_key, parent_indent) {
        // Only trigger when the actual line indentation is 0 (dangling) and parent was at zero indent
        if line_indent == 0 && p_indent == 0 {
            let key = stripped.split(':').next().unwrap_or("").trim();
            if parent == "metadata" && KNOWN_METADATA_CHILD_KEYS.contains(&key) {
                let expected = p_indent + 2;
                let mut out = String::with_capacity(expected + stripped.len());
                out.push_str(&" ".repeat(expected));
                out.push_str(stripped);
                return out;
            }
        }
    }

    line.to_string()
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_expands_tabs() {
        assert_eq!(apply_tab_expansion("\tkey: val"), "  key: val");
        assert_eq!(apply_tab_expansion("\t\tnested: val"), "    nested: val");
    }

    #[test]
    fn test_snaps_odd_indent_to_grid() {
        assert_eq!(apply_snap_to_grid(" key: val"), "  key: val");
        assert_eq!(apply_snap_to_grid("   nested: val"), "  nested: val");
        assert_eq!(apply_snap_to_grid("     deep: val"), "    deep: val");
    }

    #[test]
    fn test_preserves_even_indent() {
        assert_eq!(apply_snap_to_grid("  key: val"), "  key: val");
        assert_eq!(apply_snap_to_grid("    nested: val"), "    nested: val");
    }
}
