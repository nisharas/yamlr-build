//! Punctuation Heuristics: Magic Colon, Quote Balancing, Spacing
//!
//! Why: Developers frequently omit colons (`image nginx`), forget closing quotes
//! (`name: "web`), or omit required whitespace after markers (`-item` or `key:value`).
//! These heuristics safely repair syntax while protecting English descriptions and comments.

use lazy_static::lazy_static;
use regex::Regex;
use std::collections::HashSet;

lazy_static! {
    static ref COMMON_ENGLISH_STOPWORDS: HashSet<&'static str> = {
        let mut s = HashSet::new();
        s.insert("This");
        s.insert("The");
        s.insert("A");
        s.insert("An");
        s.insert("It");
        s.insert("If");
        s.insert("When");
        s.insert("Then");
        s.insert("For");
        s.insert("To");
        s.insert("Note");
        s.insert("But");
        s.insert("And");
        s.insert("Or");
        s
    };
    static ref RE_MAGIC_COLON: Regex = Regex::new(r"^(-\s+)?([a-zA-Z0-9_\-\.]+)\s+(.+)$").unwrap();
}

/// Injects missing colons in `key value` lines (e.g., `image nginx` -> `image: nginx`).
pub fn apply_magic_colon(line: &str, skip_punctuation: bool) -> String {
    if skip_punctuation {
        return line.to_string();
    }

    let indent_len = line.len() - line.trim_start().len();
    let indent_str = &line[..indent_len];
    let code_part = line.trim_start();

    if code_part.is_empty() || code_part.starts_with('#') || code_part.contains(':') {
        return line.to_string();
    }

    if let Some(caps) = RE_MAGIC_COLON.captures(code_part) {
        let dash_prefix = caps.get(1).map_or("", |m| m.as_str());
        let key = &caps[2];
        let val = &caps[3];

        if key != "-"
            && !key.starts_with('_')
            && !COMMON_ENGLISH_STOPWORDS.contains(key)
            && !(key.len() <= 2 && key.chars().all(|c| c.is_uppercase()))
        {
            let mut out =
                String::with_capacity(indent_len + dash_prefix.len() + key.len() + 2 + val.len());
            out.push_str(indent_str);
            out.push_str(dash_prefix);
            out.push_str(key);
            out.push_str(": ");
            out.push_str(val);
            return out;
        }
    }

    line.to_string()
}

/// Automatically balances unclosed quotes at the end of YAML values.
pub fn apply_quote_balancing(line: &str, skip_punctuation: bool) -> String {
    if skip_punctuation || !line.contains(':') {
        return line.to_string();
    }

    if let Some(idx) = line.find(':') {
        let rest = &line[idx + 1..];
        let (val_part, comment_part) = if let Some(hash_idx) = rest.find('#') {
            (&rest[..hash_idx], &rest[hash_idx..])
        } else {
            (rest, "")
        };

        let val_trimmed = val_part.trim();
        if val_trimmed.is_empty() {
            return line.to_string();
        }

        let first = val_trimmed.chars().next().unwrap();
        if first == '"' || first == '\'' {
            let quote_count = val_trimmed.chars().filter(|&c| c == first).count();
            if quote_count % 2 != 0 && !val_trimmed.ends_with(first) {
                let trimmed_end = line.trim_end();
                if comment_part.is_empty() {
                    let mut out = trimmed_end.to_string();
                    out.push(first);
                    return out;
                } else {
                    // Rebuild with closing quote before comment
                    let mut out = line[..idx + 1].to_string();
                    out.push_str(val_part.trim_end());
                    out.push(first);
                    out.push(' ');
                    out.push_str(comment_part.trim_start());
                    return out;
                }
            }
        }
    }

    line.to_string()
}

/// Normalizes missing whitespace after list dashes (`-item` -> `- item`)
/// and colons (`key:value` -> `key: value`).
pub fn apply_spacing(line: &str, skip_punctuation: bool) -> String {
    if skip_punctuation {
        return line.to_string();
    }

    let stripped = line.trim_start();
    let indent_len = line.len() - stripped.len();
    let indent_str = &line[..indent_len];

    // 1. Dash spacing "-item" -> "- item"
    if stripped.starts_with('-')
        && !stripped.starts_with("---")
        && stripped.len() > 1
        && !stripped.chars().nth(1).unwrap().is_whitespace()
    {
        let mut out = String::with_capacity(indent_len + 2 + stripped.len() - 1);
        out.push_str(indent_str);
        out.push_str("- ");
        out.push_str(&stripped[1..]);
        return out;
    }

    // 2. Colon spacing "key:value" -> "key: value"
    if let Some(colon_idx) = find_unquoted_colon(stripped) {
        let before_colon = &stripped[..colon_idx];
        let after_colon = &stripped[colon_idx + 1..];

        // Ensure key doesn't have spaces and after_colon is non-empty and doesn't start with space
        if !before_colon.contains(' ')
            && !after_colon.is_empty()
            && !after_colon.starts_with(' ')
            && !after_colon.starts_with('/')
        // Avoid breaking URLs like http://
        {
            let mut out =
                String::with_capacity(indent_len + before_colon.len() + 2 + after_colon.len());
            out.push_str(indent_str);
            out.push_str(before_colon);
            out.push_str(": ");
            out.push_str(after_colon);
            return out;
        }
    }

    line.to_string()
}

fn find_unquoted_colon(text: &str) -> Option<usize> {
    let mut quote = None;
    let mut escaped = false;
    let mut chars = text.char_indices().peekable();

    while let Some((index, ch)) = chars.next() {
        if let Some(quote_char) = quote {
            if quote_char == '"' && escaped {
                escaped = false;
            } else if quote_char == '"' && ch == '\\' {
                escaped = true;
            } else if quote_char == '\''
                && ch == '\''
                && chars.peek().map(|(_, next)| *next == '\'').unwrap_or(false)
            {
                chars.next();
            } else if ch == quote_char {
                quote = None;
            }
        } else if ch == '"' || ch == '\'' {
            quote = Some(ch);
        } else if ch == ':' {
            return Some(index);
        }
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_magic_colon_recovers_missing_colon() {
        assert_eq!(apply_magic_colon("image nginx", false), "image: nginx");
        assert_eq!(
            apply_magic_colon("  name web-service", false),
            "  name: web-service"
        );
        assert_eq!(
            apply_magic_colon("- containerPort 80", false),
            "- containerPort: 80"
        );
    }

    #[test]
    fn test_magic_colon_ignores_stopwords() {
        assert_eq!(
            apply_magic_colon("This is a description", false),
            "This is a description"
        );
        assert_eq!(
            apply_magic_colon("Note that pods restart", false),
            "Note that pods restart"
        );
    }

    #[test]
    fn test_quote_balancing() {
        assert_eq!(
            apply_quote_balancing("image: \"nginx:latest", false),
            "image: \"nginx:latest\""
        );
        assert_eq!(
            apply_quote_balancing("env: 'production", false),
            "env: 'production'"
        );
    }

    #[test]
    fn test_spacing_repairs() {
        assert_eq!(apply_spacing("-item", false), "- item");
        assert_eq!(apply_spacing("key:value", false), "key: value");
        assert_eq!(
            apply_spacing("url: http://localhost", false),
            "url: http://localhost"
        );
        assert_eq!(
            apply_spacing("  \"quoted:key\": value", false),
            "  \"quoted:key\": value"
        );
        assert_eq!(
            apply_spacing("  'quoted:key': value", false),
            "  'quoted:key': value"
        );
    }
}
