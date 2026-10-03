//! Fragmented Sequence Heuristic
//!
//! Why: Copy-paste accidents often result in broken sequence bullets such as
//! `- - item` or `-- item`. This heuristic normalizes them to a single `- item`.

/// Normalizes fragmented sequence indicators.
pub fn apply_fragmented_sequence(line: &str, in_block: bool) -> String {
    if in_block {
        return line.to_string();
    }

    let stripped = line.trim_start();
    let indent_len = line.len() - stripped.len();
    let indent_str = &line[..indent_len];

    // 1. Double dash separated: "- - item" -> "- item"
    if stripped.starts_with("- -") {
        let rest = stripped[3..].trim_start();
        let mut out = String::with_capacity(indent_len + 2 + rest.len());
        out.push_str(indent_str);
        out.push_str("- ");
        out.push_str(rest);
        return out;
    }

    // 2. Double dash fused: "-- item" -> "- item" (ignore "---" doc boundary)
    if stripped.starts_with("--") && !stripped.starts_with("---") {
        let rest = stripped[2..].trim_start();
        let mut out = String::with_capacity(indent_len + 2 + rest.len());
        out.push_str(indent_str);
        out.push_str("- ");
        out.push_str(rest);
        return out;
    }

    line.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalizes_double_dash_sequence() {
        assert_eq!(apply_fragmented_sequence("  - - item1", false), "  - item1");
        assert_eq!(apply_fragmented_sequence("  -- item2", false), "  - item2");
    }

    #[test]
    fn test_preserves_doc_boundary() {
        assert_eq!(apply_fragmented_sequence("---", false), "---");
    }
}
