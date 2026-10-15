//! Canonical Kubernetes manifest formatter and fixer (k8sfmt / yamlfix).
//!
//! Provides deterministic schema-based key ordering and layout normalization,
//! operating in-place (-w), streaming to stdout, or processing piped stdin (-).

use clap::{Arg, ArgAction, Command};
use std::fs;
use std::io::{self, Read};
use std::path::Path;
use walkdir::WalkDir;

use crate::cli::{EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_USAGE, EXIT_VIOLATIONS};
use crate::healing::{native_reconstruct_from_semantic, native_sort_keys};
use crate::sharder::native_shard;
use crate::structurer::native_structurize;

pub fn execute_fmt(args: &[String]) -> i32 {
    let (target, write_in_place) = match parse_fmt_args(args) {
        Ok(parsed) => parsed,
        Err(error) => return crate::cli::report_argument_error(error),
    };

    if target == "-" {
        let mut content = String::new();
        if let Err(error) = io::stdin().read_to_string(&mut content) {
            eprintln!("[ERROR] Failed to read manifest from stdin: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
        let formatted = format_manifest_content(&content);
        print!("{}", formatted);
        return EXIT_SUCCESS;
    }

    let path = Path::new(&target);
    if path.is_file() {
        let content = match fs::read_to_string(path) {
            Ok(content) => content,
            Err(error) => {
                eprintln!("[ERROR] Failed to read '{}': {}", path.display(), error);
                return EXIT_SYSTEM_ERROR;
            }
        };
        let formatted = format_manifest_content(&content);
        if write_in_place {
            if formatted != content {
                if let Err(error) = fs::write(path, &formatted) {
                    eprintln!("[ERROR] Failed to write '{}': {}", path.display(), error);
                    return EXIT_SYSTEM_ERROR;
                }
                println!("{}", path.display());
            }
        } else {
            print!("{}", formatted);
        }
        return EXIT_SUCCESS;
    } else if path.is_dir() {
        let mut diff_count = 0;
        for entry in WalkDir::new(path) {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    eprintln!("[ERROR] Failed to traverse '{}': {}", path.display(), error);
                    return EXIT_SYSTEM_ERROR;
                }
            };
            let p = entry.path();
            if p.is_file() {
                if let Some(ext) = p.extension() {
                    if ext == "yaml" || ext == "yml" {
                        let content = match fs::read_to_string(p) {
                            Ok(content) => content,
                            Err(error) => {
                                eprintln!("[ERROR] Failed to read '{}': {}", p.display(), error);
                                return EXIT_SYSTEM_ERROR;
                            }
                        };
                        let formatted = format_manifest_content(&content);
                        if formatted != content {
                            diff_count += 1;
                            if write_in_place {
                                if let Err(error) = fs::write(p, &formatted) {
                                    eprintln!(
                                        "[ERROR] Failed to write '{}': {}",
                                        p.display(),
                                        error
                                    );
                                    return EXIT_SYSTEM_ERROR;
                                }
                                println!("{}", p.display());
                            } else {
                                println!("{}", p.display());
                            }
                        }
                    }
                }
            }
        }
        if !write_in_place && diff_count > 0 {
            return EXIT_VIOLATIONS;
        }
        return EXIT_SUCCESS;
    }

    eprintln!("[ERROR] Target path '{}' does not exist.", target);
    EXIT_USAGE
}

pub(crate) fn parse_fmt_args(args: &[String]) -> Result<(String, bool), clap::Error> {
    let parsed = crate::cli::parse_command_args(
        Command::new("fmt")
            .about("Format manifests; writes require --write (stdin is '-')")
            .arg(Arg::new("target").default_value("."))
            .arg(
                Arg::new("write")
                    .long("write")
                    .short('w')
                    .action(ArgAction::SetTrue),
            ),
        args,
    )?;
    Ok((
        parsed.get_one::<String>("target").unwrap().clone(),
        parsed.get_flag("write"),
    ))
}

pub fn execute_fix(args: &[String]) -> i32 {
    let modified_args = fix_arguments(args);
    crate::cli::heal_cmd::execute_heal(&modified_args)
}

fn fix_arguments(args: &[String]) -> Vec<String> {
    let mut modified_args = args.to_vec();
    let option_end = args.iter().position(|a| a == "--").unwrap_or(args.len());
    if !args
        .iter()
        .take(option_end)
        .skip(2)
        .any(|a| a == "--apply" || a == "-a")
    {
        modified_args.insert(option_end, "--apply".to_string());
    }
    modified_args
}

#[cfg(test)]
mod argument_tests {
    use super::*;

    #[test]
    fn formatter_accepts_stdin_and_literal_option_paths() {
        for target in ["-", "--write"] {
            let args = vec!["yamlr".into(), "fmt".into(), "--".into(), target.into()];
            assert_eq!(parse_fmt_args(&args).unwrap(), (target.into(), false));
        }
    }

    #[test]
    fn formatter_rejects_duplicate_flags_and_targets() {
        for tail in [vec!["-w", "--write"], vec!["one", "two"], vec!["--unknown"]] {
            let mut args = vec!["yamlr".into(), "fmt".into()];
            args.extend(tail.into_iter().map(String::from));
            assert!(parse_fmt_args(&args).is_err());
        }
    }

    #[test]
    fn fix_inserts_apply_before_option_terminator() {
        let args = vec!["yamlr".into(), "fix".into(), "--".into(), "--apply".into()];
        assert_eq!(
            fix_arguments(&args),
            vec!["yamlr", "fix", "--apply", "--", "--apply"]
        );
    }
}

pub fn format_manifest_content(content: &str) -> String {
    if content.trim().is_empty() {
        return content.to_string();
    }

    let docs: Vec<&str> = crate::parsers::streaming::stream_document_slices(content).collect();
    if docs.len() > 1 {
        let mut formatted_docs = Vec::new();
        for doc in docs {
            let shards = native_shard(doc);
            if shards.is_empty() {
                formatted_docs.push(doc.to_string());
            } else {
                let mut manifest = native_structurize(shards);
                native_sort_keys(&mut manifest.root, 0);
                let formatted = native_reconstruct_from_semantic(&manifest);
                formatted_docs.push(formatted);
            }
        }
        let has_leading = content.trim_start().starts_with("---");
        let combined = formatted_docs.join("\n---\n");
        return if has_leading {
            format!("---\n{}", combined)
        } else {
            combined
        };
    }

    let shards = native_shard(content);
    if shards.is_empty() {
        return content.to_string();
    }
    let mut manifest = native_structurize(shards);
    native_sort_keys(&mut manifest.root, 0);
    native_reconstruct_from_semantic(&manifest)
}
