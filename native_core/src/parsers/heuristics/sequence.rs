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
    // CRITICAL GUARD: Only match "- - " (with space after 2nd dash), and rest must NOT start with '-' (CLI flags like "- -c" or "- --flag")
    if stripped.starts_with("- - ") {
        let rest = stripped[4..].trim_start();
        if !rest.starts_with('-') {
            let mut out = String::with_capacity(indent_len + 2 + rest.len());
            out.push_str(indent_str);
            out.push_str("- ");
            out.push_str(rest);
            return out;
        }
    }

    // 2. Double dash fused: "-- item" -> "- item" (ignore "---" doc boundary and CLI flags like "--flag")
    if stripped.starts_with("-- ") && !stripped.starts_with("---") {
        let rest = stripped[3..].trim_start();
        if !rest.starts_with('-') {
            let mut out = String::with_capacity(indent_len + 2 + rest.len());
            out.push_str(indent_str);
            out.push_str("- ");
            out.push_str(rest);
            return out;
        }
    }

    // Trap 24: Accidental Markdown checklist syntax: `- [ ] feature` or `- [x] feature`
    // In YAML, `[` opens an invalid flow-sequence if followed by plain words. Wrap in quotes to preserve content.
    if stripped.starts_with("- [ ] ") || stripped.starts_with("- [x] ") || stripped.starts_with("- [X] ") {
        let tag = &stripped[..6]; // e.g. "- [ ] "
        let rest = &stripped[6..];
        let mut out = String::with_capacity(indent_len + 3 + tag.len() + rest.len() + 1);
        out.push_str(indent_str);
        out.push_str("- \"");
        out.push_str(&tag[2..]);
        out.push_str(rest);
        out.push('"');
        return out;
    }

    line.to_string()
}

/// Normalizes Docker Compose / `.env` style syntax (`- KEY=VALUE`) under `env:` sequence mappings
/// into canonical Kubernetes container env structure (`- name: KEY\n  value: "VALUE"` or flow `{ name: KEY, value: "VALUE" }`).
pub fn apply_env_key_value_sequence(line: &str, parent_key: Option<&str>, in_block: bool) -> String {
    if in_block {
        return line.to_string();
    }

    let is_env_parent = parent_key.map(|p| p.eq_ignore_ascii_case("env")).unwrap_or(false);
    if !is_env_parent {
        return line.to_string();
    }

    let stripped = line.trim_start();
    let indent_len = line.len() - stripped.len();
    let indent_str = &line[..indent_len];

    // Check for sequence item starting with `- ` followed by `KEY=VALUE`
    if stripped.starts_with("- ") {
        let item = stripped[2..].trim();
        // Ensure no colon in item (not already a valid mapping e.g. "- name: FOO")
        if !item.contains(':') && item.contains('=') {
            if let Some(eq_idx) = item.find('=') {
                let key = item[..eq_idx].trim();
                let val = item[eq_idx + 1..].trim();

                // Validate key conforms to valid shell environment variable identifier: ^[A-Za-z_][A-Za-z0-9_]*$
                let is_valid_identifier = !key.is_empty()
                    && (key.starts_with(|c: char| c.is_ascii_alphabetic() || c == '_'))
                    && key.chars().all(|c| c.is_ascii_alphanumeric() || c == '_');

                if is_valid_identifier {
                    // Canonical format: "- name: KEY\n    value: \"VAL\""
                    let val_quoted = if (val.starts_with('"') && val.ends_with('"'))
                        || (val.starts_with('\'') && val.ends_with('\''))
                    {
                        val.to_string()
                    } else {
                        format!("\"{}\"", val)
                    };

                    let mut out = String::with_capacity(indent_len + 30 + key.len() + val_quoted.len());
                    out.push_str(indent_str);
                    out.push_str("- name: ");
                    out.push_str(key);
                    out.push('\n');
                    out.push_str(indent_str);
                    out.push_str("  value: ");
                    out.push_str(&val_quoted);
                    return out;
                }
            }
        }
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

    #[test]
    fn test_markdown_checklist_sequence() {
        assert_eq!(
            apply_fragmented_sequence("- [ ] feature-flag-a", false),
            "- \"[ ] feature-flag-a\""
        );
        assert_eq!(
            apply_fragmented_sequence("  - [x] deploy database", false),
            "  - \"[x] deploy database\""
        );
    }

    #[test]
    fn test_env_key_value_sequence() {
        // Trap 32: Docker compose / .env syntax in container env
        let line = "  - APP_ENV=production";
        let healed = apply_env_key_value_sequence(line, Some("env"), false);
        assert_eq!(healed, "  - name: APP_ENV\n    value: \"production\"");

        let line_quoted = "  - DB_HOST=\"postgres.internal\"";
        let healed_quoted = apply_env_key_value_sequence(line_quoted, Some("env"), false);
        assert_eq!(healed_quoted, "  - name: DB_HOST\n    value: \"postgres.internal\"");

        // Negative check: Not applied if parent_key is NOT env (e.g. args, command)
        let non_env_line = "  - --flag=value";
        let untouched = apply_env_key_value_sequence(non_env_line, Some("args"), false);
        assert_eq!(untouched, "  - --flag=value");

        // Negative check: Normal k8s format is untouched
        let valid_k8s = "  - name: PORT";
        let untouched_k8s = apply_env_key_value_sequence(valid_k8s, Some("env"), false);
        assert_eq!(untouched_k8s, "  - name: PORT");
    }
}
