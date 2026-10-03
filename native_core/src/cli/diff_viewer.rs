//! Interactive Terminal Inline Word Diff Viewer.
//!
//! Why: Standard unified diffs highlight entire lines in red/green, obscuring the precise
//! semantic token or image tag that changed. This module computes word- and token-level
//! diffs (similar to delta and git diff --color-words), providing instant visual clarity.

use clap::{Arg, ArgAction, Command};
use std::env;

/// Renders a colorized, syntax-aware inline word diff to stdout.
pub fn render_inline_diff(original: &str, healed: &str) {
    let use_color =
        env::var("NO_COLOR").is_err() && env::var("TERM").map(|t| t != "dumb").unwrap_or(true);
    let orig_lines: Vec<&str> = original.lines().collect();
    let healed_lines: Vec<&str> = healed.lines().collect();

    println!("       --- original");
    println!("       +++ healed (yamlr auto-repair)");

    let max_lines = orig_lines.len().max(healed_lines.len());
    for i in 0..max_lines {
        let o = orig_lines.get(i);
        let h = healed_lines.get(i);
        match (o, h) {
            (Some(ol), Some(hl)) if ol != hl => {
                let (fmt_old, fmt_new) = format_inline_word_diff(ol, hl, use_color);
                println!("       - {:3} | {}", i + 1, fmt_old);
                println!("       + {:3} | {}", i + 1, fmt_new);
            }
            (Some(ol), None) => {
                if use_color {
                    println!("       \x1b[31m- {:3} | {}\x1b[0m", i + 1, ol);
                } else {
                    println!("       - {:3} | {}", i + 1, ol);
                }
            }
            (None, Some(hl)) => {
                if use_color {
                    println!("       \x1b[32m+ {:3} | {}\x1b[0m", i + 1, hl);
                } else {
                    println!("       + {:3} | {}", i + 1, hl);
                }
            }
            _ => {}
        }
    }
}

/// Tokenizes two lines and highlights the exact replacement tokens.
pub fn format_inline_word_diff(
    old_line: &str,
    new_line: &str,
    use_color: bool,
) -> (String, String) {
    let old_tokens = tokenize_line(old_line);
    let new_tokens = tokenize_line(new_line);

    // Compute common prefix length
    let mut prefix_len = 0;
    while prefix_len < old_tokens.len()
        && prefix_len < new_tokens.len()
        && old_tokens[prefix_len] == new_tokens[prefix_len]
    {
        prefix_len += 1;
    }

    // Compute common suffix length
    let mut old_suffix = old_tokens.len();
    let mut new_suffix = new_tokens.len();
    while old_suffix > prefix_len
        && new_suffix > prefix_len
        && old_tokens[old_suffix - 1] == new_tokens[new_suffix - 1]
    {
        old_suffix -= 1;
        new_suffix -= 1;
    }

    let prefix: String = old_tokens[..prefix_len].join("");
    let old_changed: String = old_tokens[prefix_len..old_suffix].join("");
    let new_changed: String = new_tokens[prefix_len..new_suffix].join("");
    let suffix: String = old_tokens[old_suffix..].join("");

    if use_color {
        let fmt_old = format!(
            "{}\x1b[31;1m\x1b[4m{}\x1b[0m{}",
            prefix, old_changed, suffix
        );
        let fmt_new = format!(
            "{}\x1b[32;1m\x1b[4m{}\x1b[0m{}",
            prefix, new_changed, suffix
        );
        (fmt_old, fmt_new)
    } else {
        let fmt_old = format!("{}[- {} -]{}", prefix, old_changed, suffix);
        let fmt_new = format!("{}[+ {} +]{}", prefix, new_changed, suffix);
        (fmt_old, fmt_new)
    }
}

/// Tokenizes a YAML line into word chunks and punctuation tokens.
fn tokenize_line(line: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut in_whitespace = false;

    for ch in line.chars() {
        if ch.is_whitespace() {
            if !in_whitespace && !current.is_empty() {
                tokens.push(current);
                current = String::new();
            }
            in_whitespace = true;
            current.push(ch);
        } else if ch == ':' || ch == '-' || ch == '"' || ch == '\'' || ch == '/' || ch == '.' {
            if !current.is_empty() {
                tokens.push(current);
                current = String::new();
            }
            in_whitespace = false;
            tokens.push(ch.to_string());
        } else {
            if in_whitespace && !current.is_empty() {
                tokens.push(current);
                current = String::new();
            }
            in_whitespace = false;
            current.push(ch);
        }
    }
    if !current.is_empty() {
        tokens.push(current);
    }
    tokens
}

/// Executes the standalone `yamlr diff <PATH>` command to preview proposed changes.
pub fn execute_diff(args: &[String]) -> i32 {
    let parsed = match parse_diff_arguments(args) {
        Ok(parsed) => parsed,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target = parsed
        .get_one::<String>("target")
        .map(String::as_str)
        .unwrap_or(".");
    let unified = parsed.get_flag("unified");

    let path = std::path::Path::new(target);
    if !path.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target);
        return crate::cli::EXIT_CONFIG_ERROR;
    }

    let total_diffs = if path.is_file() {
        match preview_file_diff(path, unified) {
            Ok(has_diff) => usize::from(has_diff),
            Err(error) => {
                eprintln!("[ERROR] Diff preview incomplete: {}", error);
                return crate::cli::EXIT_SYSTEM_ERROR;
            }
        }
    } else {
        match preview_yaml_entries(walkdir::WalkDir::new(path), unified) {
            Ok(total_diffs) => total_diffs,
            Err(error) => {
                eprintln!("[ERROR] Diff preview incomplete: {}", error);
                return crate::cli::EXIT_SYSTEM_ERROR;
            }
        }
    };

    if total_diffs > 0 {
        crate::cli::EXIT_VIOLATIONS
    } else {
        println!("[OK] No remediation diffs required for '{}'.", target);
        crate::cli::EXIT_SUCCESS
    }
}

pub(crate) fn parse_diff_arguments(args: &[String]) -> Result<clap::ArgMatches, clap::Error> {
    let command = Command::new("diff")
        .disable_version_flag(true)
        .arg(Arg::new("target").value_name("PATH").num_args(0..=1))
        .arg(
            Arg::new("unified")
                .long("unified")
                .short('u')
                .action(ArgAction::SetTrue),
        );
    crate::cli::parse_command_args(command, args)
}

/// Renders standard Git-compatible unified diff format with @@ chunk headers.
pub fn render_unified_diff(original: &str, healed: &str, file_name: &str) {
    let orig_lines: Vec<&str> = original.lines().collect();
    let healed_lines: Vec<&str> = healed.lines().collect();

    println!("--- a/{}", file_name);
    println!("+++ b/{}", file_name);

    let max_lines = orig_lines.len().max(healed_lines.len());
    let mut in_hunk = false;

    for i in 0..max_lines {
        let o = orig_lines.get(i);
        let h = healed_lines.get(i);
        if o != h {
            if !in_hunk {
                println!(
                    "@@ -{},{} +{},{} @@",
                    i + 1,
                    orig_lines.len().saturating_sub(i).min(5),
                    i + 1,
                    healed_lines.len().saturating_sub(i).min(5)
                );
                in_hunk = true;
            }
            if let Some(ol) = o {
                println!("-{}", ol);
            }
            if let Some(hl) = h {
                println!("+{}", hl);
            }
        } else {
            in_hunk = false;
        }
    }
}

fn preview_yaml_entries<I>(entries: I, unified: bool) -> Result<usize, String>
where
    I: IntoIterator<Item = Result<walkdir::DirEntry, walkdir::Error>>,
{
    let mut total_diffs = 0;
    for entry in entries {
        let entry = entry.map_err(|error| format!("Failed to traverse diff target: {}", error))?;
        let path = entry.path();
        if !path.is_file()
            || !path
                .extension()
                .is_some_and(|extension| extension == "yaml" || extension == "yml")
        {
            continue;
        }
        if preview_file_diff(path, unified)? {
            total_diffs += 1;
        }
    }
    Ok(total_diffs)
}

fn preview_file_diff(path: &std::path::Path, unified: bool) -> Result<bool, String> {
    let content = std::fs::read_to_string(path)
        .map_err(|error| format!("Cannot read manifest '{}': {}", path.display(), error))?;
    let (healed, changes) = crate::cli::heal_cmd::heal_manifest_string(&content);
    if changes.is_empty() || healed == content {
        return Ok(false);
    }
    let display_path = crate::path_utils::normalize_display_path(path);
    println!("\n=== Diff: {} ===", display_path);
    for c in &changes {
        println!("       + {}", c);
    }
    if unified {
        render_unified_diff(&content, &healed, &display_path);
    } else {
        render_inline_diff(&content, &healed);
    }
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_format_inline_word_diff_plain() {
        let old = "  apiVersion: extensions/v1beta1";
        let new = "  apiVersion: apps/v1";
        let (fmt_old, fmt_new) = format_inline_word_diff(old, new, false);
        assert!(fmt_old.contains("[- extensions/v1beta1 -]"));
        assert!(fmt_new.contains("[+ apps/v1 +]"));
        assert!(fmt_old.starts_with("  apiVersion: "));
        assert!(fmt_new.starts_with("  apiVersion: "));
    }

    #[test]
    fn test_format_inline_word_diff_color() {
        let old = "  image: redis:latest # cache";
        let new = "  image: redis:stable-pinned # cache";
        let (fmt_old, fmt_new) = format_inline_word_diff(old, new, true);
        assert!(fmt_old.contains("\x1b[31;1m\x1b[4mlatest\x1b[0m"));
        assert!(fmt_new.contains("\x1b[32;1m\x1b[4mstable-pinned\x1b[0m"));
    }

    #[test]
    fn test_render_unified_diff() {
        let old = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: old-name";
        let new = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: new-name";
        // Ensure render_unified_diff executes without panic
        render_unified_diff(old, new, "pod.yaml");
    }

    #[test]
    fn directory_preview_propagates_traversal_errors() {
        let dir = tempdir().unwrap();
        let missing = dir.path().join("missing");

        let error = preview_yaml_entries(walkdir::WalkDir::new(missing), false).unwrap_err();

        assert!(error.contains("Failed to traverse diff target"));
    }

    #[test]
    fn file_preview_propagates_read_errors() {
        let dir = tempdir().unwrap();
        let manifest = dir.path().join("invalid-encoding.yaml");
        std::fs::write(&manifest, [0xff, 0xfe]).unwrap();

        let error = preview_file_diff(&manifest, false).unwrap_err();

        assert!(error.contains("Cannot read manifest"));
    }

    #[test]
    fn diff_options_can_appear_before_or_after_the_target() {
        let dir = tempdir().unwrap();
        let manifest = dir.path().join("pod.yaml");
        std::fs::write(
            &manifest,
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: sample\n",
        )
        .unwrap();
        let manifest = manifest.to_str().unwrap().to_string();

        let flag_first = vec![
            "yamlr".into(),
            "diff".into(),
            "--unified".into(),
            manifest.clone(),
        ];
        let flag_last = vec!["yamlr".into(), "diff".into(), manifest, "-u".into()];

        assert_eq!(execute_diff(&flag_first), crate::cli::EXIT_SUCCESS);
        assert_eq!(execute_diff(&flag_last), crate::cli::EXIT_SUCCESS);
    }

    #[test]
    fn diff_parser_rejects_unknown_options_and_extra_targets() {
        for args in [
            vec!["yamlr", "diff", "--typo"],
            vec!["yamlr", "diff", "one.yaml", "two.yaml"],
        ] {
            let args = args.into_iter().map(str::to_string).collect::<Vec<_>>();
            assert!(parse_diff_arguments(&args).is_err());
        }
    }

    #[test]
    fn diff_rejects_unknown_options_and_multiple_targets() {
        let unknown = vec!["yamlr".into(), "diff".into(), "--xml".into()];
        let multiple = vec![
            "yamlr".into(),
            "diff".into(),
            "one.yaml".into(),
            "two.yaml".into(),
        ];

        assert_eq!(execute_diff(&unknown), crate::cli::EXIT_USAGE);
        assert_eq!(execute_diff(&multiple), crate::cli::EXIT_USAGE);
    }

    #[test]
    fn diff_double_dash_allows_a_dash_prefixed_target() {
        let args = vec![
            "yamlr".into(),
            "diff".into(),
            "--".into(),
            "-manifest.yaml".into(),
        ];

        assert_eq!(execute_diff(&args), crate::cli::EXIT_CONFIG_ERROR);
    }
}
