//! Boolean Guard Heuristic
//!
//! Why: In YAML 1.1, unquoted strings like `yes`, `no`, `y`, `n`, `on`, `off` are parsed
//! as booleans rather than strings. In Kubernetes manifests (especially ConfigMaps,
//! environment variables, and labels), this causes "The Norway Problem" (NO -> false).
//! This heuristic detects unquoted YAML 1.1 booleans and wraps them in deterministic quotes.

use lazy_static::lazy_static;
use std::collections::HashSet;

lazy_static! {
    static ref BOOLEAN_STRINGS: HashSet<&'static str> = {
        let mut s = HashSet::new();
        s.insert("yes");
        s.insert("Yes");
        s.insert("YES");
        s.insert("no");
        s.insert("No");
        s.insert("NO");
        s.insert("y");
        s.insert("Y");
        s.insert("n");
        s.insert("N");
        s.insert("on");
        s.insert("On");
        s.insert("ON");
        s.insert("off");
        s.insert("Off");
        s.insert("OFF");
        s
    };
}

/// Applies boolean guard quoting to a single raw line.
pub fn apply_boolean_guard(line: &str, in_block: bool) -> String {
    if in_block || !line.contains(':') {
        return line.to_string();
    }

    // Don't touch comment-only lines
    let trimmed_left = line.trim_start();
    if trimmed_left.starts_with('#') {
        return line.to_string();
    }

    // Partition by the first colon
    if let Some(idx) = line.find(':') {
        let key_part = &line[..idx];
        let rest = &line[idx + 1..];

        // If there's an inline comment, split it
        let (val_part, comment_part) = if let Some(hash_idx) = rest.find('#') {
            // Ensure hash isn't inside quotes
            let before_hash = &rest[..hash_idx];
            let after_hash = &rest[hash_idx..];
            (before_hash, after_hash)
        } else {
            (rest, "")
        };

        let trimmed_val = val_part.trim();
        if trimmed_val.is_empty() {
            return line.to_string();
        }

        // Check if value is already quoted
        if (trimmed_val.starts_with('"') && trimmed_val.ends_with('"') && trimmed_val.len() >= 2)
            || (trimmed_val.starts_with('\'')
                && trimmed_val.ends_with('\'')
                && trimmed_val.len() >= 2)
        {
            return line.to_string();
        }

        // Check against YAML 1.1 boolean set
        let is_env_boolean_value = key_part.trim() == "value" && (trimmed_val == "true" || trimmed_val == "false");
        if BOOLEAN_STRINGS.contains(trimmed_val) || is_env_boolean_value {
            // Find whitespace preceding the value
            let val_start = val_part.find(trimmed_val).unwrap_or(0);
            let space_before = &val_part[..val_start];
            let space_after = &val_part[val_start + trimmed_val.len()..];

            let mut out = String::with_capacity(line.len() + 2);
            out.push_str(key_part);
            out.push(':');
            out.push_str(space_before);
            out.push('"');
            out.push_str(trimmed_val);
            out.push('"');
            out.push_str(space_after);
            out.push_str(comment_part);
            return out;
        }
    }

    line.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quotes_norway_problem_booleans() {
        assert_eq!(apply_boolean_guard("country: NO", false), "country: \"NO\"");
        assert_eq!(
            apply_boolean_guard("enabled: yes", false),
            "enabled: \"yes\""
        );
        assert_eq!(
            apply_boolean_guard("debug: off # toggle", false),
            "debug: \"off\" # toggle"
        );
        assert_eq!(apply_boolean_guard("flag: on", false), "flag: \"on\"");
    }

    #[test]
    fn test_preserves_already_quoted_and_real_booleans() {
        assert_eq!(
            apply_boolean_guard("country: \"NO\"", false),
            "country: \"NO\""
        );
        assert_eq!(apply_boolean_guard("enabled: true", false), "enabled: true");
        assert_eq!(
            apply_boolean_guard("enabled: false", false),
            "enabled: false"
        );
    }

    #[test]
    fn test_ignores_block_scalar() {
        assert_eq!(apply_boolean_guard("no", true), "no");
    }
}
