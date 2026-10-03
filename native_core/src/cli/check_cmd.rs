//! Strict non-healing manifest linter and gate for CI/CD pipelines.
//!
//! Why: CI environments require a strict verification command (`yamlr check`)
//! that guarantees zero disk modifications and returns deterministic exit codes:
//! 0 for clean manifests, 1 for policy/schema violations, 2 for parse/syntax errors.

use std::fmt::Display;
use std::path::{Path, PathBuf};
use std::time::Instant;
use walkdir::WalkDir;

use crate::cli::{
    scan_cmd::{process_file, scan_fail_on::FailOn},
    EXIT_SUCCESS, EXIT_SYNTAX_ERROR, EXIT_SYSTEM_ERROR, EXIT_USAGE, EXIT_VIOLATIONS,
};
use crate::schemas::native_get_schema_for_version;
use clap::{Arg, ArgAction, Command};

/// Executes the strict non-healing check command.
///
/// Why: Provides an auditable read-only lint pass preventing accidental file mutations
/// in automated CI checks, git pre-commit hooks, or review gates.
pub fn execute_check(args: &[String]) -> i32 {
    let parsed = match parse_check_arguments(args) {
        Ok(parsed) => parsed,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let start_time = Instant::now();
    let target = parsed
        .get_one::<String>("target")
        .map(String::as_str)
        .unwrap_or(".");
    let k8s_version = parsed
        .get_one::<String>("k8s-version")
        .map(String::as_str)
        .unwrap_or("1.30");
    let quiet = parsed.get_flag("quiet");
    if let Err(error) = crate::schemas::validate_k8s_version(k8s_version) {
        eprintln!("[ERROR] {}", error);
        return EXIT_USAGE;
    }
    if let Err(error) = crate::schemas::bundler::validate_schema_overrides(k8s_version) {
        eprintln!("[ERROR] {}", error);
        return EXIT_SYSTEM_ERROR;
    }
    let fail_on_value = parsed
        .get_one::<String>("fail-on")
        .map(String::as_str)
        .unwrap_or("error");
    let fail_on = match FailOn::parse(fail_on_value) {
        Some(threshold) => threshold,
        None => {
            eprintln!("[ERROR] Unsupported --fail-on value '{}'. Use error, warning, note, any, info, or none.", fail_on_value);
            return EXIT_USAGE;
        }
    };

    let schemas = native_get_schema_for_version(k8s_version);
    let path = Path::new(target);

    if !path.exists() {
        if !quiet {
            eprintln!("[ERROR] Target path '{}' does not exist.", target);
        }
        return EXIT_SYNTAX_ERROR;
    }

    let mut total_files = 0;
    let mut total_violations = 0;
    let mut total_integrity = 0;
    let mut results = Vec::new();

    if path.is_file() {
        total_files += 1;
        if let Err(error) = process_file(
            path,
            &schemas,
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        ) {
            if !quiet {
                eprintln!("[ERROR] Check incomplete: {}", error);
            }
            return EXIT_SYSTEM_ERROR;
        }
    } else {
        let entries = WalkDir::new(path)
            .into_iter()
            .map(|entry| entry.map(|walk_entry| walk_entry.into_path()));
        let traversal_result = process_directory_entries(entries, |manifest_path| {
            total_files += 1;
            process_file(
                manifest_path,
                &schemas,
                &mut total_violations,
                &mut total_integrity,
                &mut results,
            )
        });
        if let Err(error) = traversal_result {
            if !quiet {
                eprintln!("[ERROR] Check incomplete: {}", error);
            }
            return EXIT_SYSTEM_ERROR;
        }
    }

    let elapsed = start_time.elapsed();

    if !quiet {
        println!("Yamlr Manifest Lint Check (Strict Non-Healing Mode)");
        println!("---------------------------------------------------");
        println!("Target:        {}", target);
        println!("K8s Schema:    v{}", k8s_version);
        println!("Files Scanned: {}", total_files);
        println!("Violations:    {}", total_violations);
        println!("Integrity:     {}", total_integrity);
        println!("Time Elapsed:  {:.2?}", elapsed);
    }

    let threshold_triggered = fail_on.is_triggered_by(&results);

    if threshold_triggered {
        if !quiet {
            println!(
                "\n[FAIL] Found manifest violations meeting the '--fail-on {}' threshold.",
                fail_on_value
            );
        }
        EXIT_VIOLATIONS
    } else {
        if !quiet {
            println!("\n[PASS] All manifests conform to Kubernetes schema and safety rules.");
        }
        EXIT_SUCCESS
    }
}

/// Parse the complete `check` grammar before execution so an unknown or
/// malformed option can never be mistaken for a target path or ignored.
pub(crate) fn parse_check_arguments(args: &[String]) -> Result<clap::ArgMatches, clap::Error> {
    let command = Command::new("check")
        .disable_help_flag(false)
        .disable_version_flag(true)
        .arg(Arg::new("target").value_name("PATH").num_args(0..=1))
        .arg(
            Arg::new("k8s-version")
                .long("k8s-version")
                .visible_alias("kube-version")
                .short('k')
                .value_name("VERSION")
                .value_parser(crate::schemas::validate_k8s_version),
        )
        .arg(
            Arg::new("fail-on")
                .long("fail-on")
                .value_name("SEVERITY")
                .value_parser(crate::cli::parse_severity_threshold),
        )
        .arg(
            Arg::new("quiet")
                .long("quiet")
                .short('q')
                .action(ArgAction::SetTrue),
        );
    crate::cli::parse_command_args(command, args)
}

fn process_directory_entries<I, E, F>(entries: I, mut process_manifest: F) -> Result<(), String>
where
    I: IntoIterator<Item = Result<PathBuf, E>>,
    E: Display,
    F: FnMut(&Path) -> Result<(), String>,
{
    for entry in entries {
        let path = entry.map_err(|error| format!("Directory traversal failed: {}", error))?;
        if path.is_file()
            && path
                .extension()
                .is_some_and(|extension| extension == "yaml" || extension == "yml")
        {
            process_manifest(&path)?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn parser_values_drive_compact_options_and_option_terminator() {
        let args = ["yamlr", "check", "-k1.31", "-q", "--", "-manifest.yaml"].map(str::to_string);
        let parsed = parse_check_arguments(&args).unwrap();
        assert_eq!(parsed.get_one::<String>("k8s-version").unwrap(), "1.31");
        assert_eq!(
            parsed.get_one::<String>("target").unwrap(),
            "-manifest.yaml"
        );
        assert!(parsed.get_flag("quiet"));
    }

    #[test]
    fn check_argument_contract_rejects_unknown_options_and_duplicate_values() {
        for tail in [
            vec!["--surprise".to_string()],
            vec!["--fail-on".to_string()],
            vec![
                "--fail-on".to_string(),
                "warning".to_string(),
                "--fail-on".to_string(),
                "error".to_string(),
            ],
            vec!["one.yaml".to_string(), "two.yaml".to_string()],
        ] {
            let mut args = vec!["yamlr".to_string(), "check".to_string()];
            args.extend(tail);
            assert!(
                parse_check_arguments(&args).is_err(),
                "accepted invalid args: {args:?}"
            );
        }
    }

    #[test]
    fn test_check_clean_manifest_exits_zero() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("clean.yaml");
        let valid_yaml = r#"
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
  namespace: default
data:
  app.conf: "debug=false"
"#;
        fs::write(&file_path, valid_yaml).unwrap();

        let args = vec![
            "yamlr".to_string(),
            "check".to_string(),
            file_path.to_str().unwrap().to_string(),
            "--quiet".to_string(),
        ];
        assert_eq!(execute_check(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_check_nonexistent_target_exits_syntax_error() {
        let args = vec![
            "yamlr".to_string(),
            "check".to_string(),
            "/non/existent/manifest/path.yaml".to_string(),
            "--quiet".to_string(),
        ];
        assert_eq!(execute_check(&args), EXIT_SYNTAX_ERROR);
    }

    #[test]
    fn test_check_violation_manifest_exits_one() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("invalid.yaml");
        let invalid_yaml = r#"
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
"#;
        fs::write(&file_path, invalid_yaml).unwrap();

        let args = vec![
            "yamlr".to_string(),
            "check".to_string(),
            file_path.to_str().unwrap().to_string(),
            "--quiet".to_string(),
        ];
        assert_eq!(execute_check(&args), EXIT_VIOLATIONS);
    }

    #[test]
    fn unreadable_manifest_exits_with_system_error_instead_of_pass() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("invalid-encoding.yaml");
        fs::write(&file_path, [0xff, 0xfe]).unwrap();
        let args = vec![
            "yamlr".to_string(),
            "check".to_string(),
            file_path.to_str().unwrap().to_string(),
            "--quiet".to_string(),
        ];

        assert_eq!(execute_check(&args), EXIT_SYSTEM_ERROR);
    }

    #[test]
    fn directory_traversal_failure_stops_check_instead_of_skipping_entries() {
        let dir = tempdir().unwrap();
        let manifest = dir.path().join("first.yaml");
        fs::write(&manifest, "kind: Pod\n").unwrap();
        let entries: Vec<Result<PathBuf, &str>> = vec![
            Ok(manifest.clone()),
            Err("permission denied"),
            Ok(dir.path().join("later.yaml")),
        ];
        let mut processed = Vec::new();

        let error = process_directory_entries(entries, |path| {
            processed.push(path.to_path_buf());
            Ok(())
        })
        .unwrap_err();

        assert!(error.contains("Directory traversal failed: permission denied"));
        assert_eq!(processed, vec![manifest]);
    }
}
