//! Deep compliance audit and forensic catalog CLI handlers in native Rust.
//!
//! Why: Enables engineering and security teams to inspect CIS benchmarks,
//! secret leakage patterns, and Kubernetes deprecation rules directly from the native binary,
//! both as an active audit scanner (`yamlr audit`) and as a catalog browser (`yamlr catalog`).

use clap::{Arg, ArgAction, Command};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;
use std::time::Instant;
use walkdir::WalkDir;

use crate::audit_engine::{get_catalog, get_deprecations, native_run_audit};
use crate::cli::{OutputFormat, EXIT_SUCCESS, EXIT_USAGE, EXIT_VIOLATIONS};

/// Executes the deep compliance audit command.
///
/// Why: Audits Kubernetes manifests against the CIS benchmark, embedded deprecation database,
/// and high-entropy secret leakage detectors.
pub fn execute_audit(args: &[String]) -> i32 {
    let start_time = Instant::now();
    let parsed = match parse_audit_arguments(args) {
        Ok(parsed) => parsed,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target = parsed.get_one::<String>("target").unwrap().as_str();
    let format_str = parsed.get_one::<String>("output").unwrap().as_str();
    let format = match OutputFormat::parse(format_str) {
        Some(format) => format,
        None => {
            eprintln!(
                "[ERROR] Unsupported --output value '{}'. Use text, json, or sarif.",
                format_str
            );
            return EXIT_USAGE;
        }
    };

    let path = Path::new(target);
    if !path.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target);
        return EXIT_VIOLATIONS;
    }

    let mut total_files = 0;
    let mut total_findings = 0;
    let mut findings_report = Vec::new();

    let mut process_file = |file_path: &Path| -> Result<(), String> {
        let content = fs::read_to_string(file_path).map_err(|error| {
            format!("Cannot read manifest '{}': {}", file_path.display(), error)
        })?;
        total_files += 1;
        let findings = native_run_audit(&content);
        for f in findings {
            total_findings += 1;
            findings_report.push(serde_json::json!({
                "file": file_path.to_string_lossy(),
                "rule_id": f.rule_id,
                "severity": f.severity,
                "title": f.check_name,
                "message": f.message,
                "line": f.line_no,
            }));
        }
        Ok(())
    };

    let processing_result = if path.is_file() {
        process_file(path)
    } else {
        process_audit_entries(WalkDir::new(path), &mut process_file)
    };
    if let Err(error) = processing_result {
        eprintln!("[ERROR] Audit incomplete: {}", error);
        return crate::cli::EXIT_SYSTEM_ERROR;
    }

    let elapsed = start_time.elapsed();

    match format {
        OutputFormat::Sarif => {
            let output = build_audit_sarif(&findings_report);
            println!(
                "{}",
                serde_json::to_string_pretty(&output).unwrap_or_default()
            );
        }
        OutputFormat::Json => {
            let output = serde_json::json!({
                "audit_version": "0.1.0",
                "target": target,
                "files_scanned": total_files,
                "total_findings": total_findings,
                "elapsed_ms": elapsed.as_millis(),
                "findings": findings_report,
            });
            println!(
                "{}",
                serde_json::to_string_pretty(&output).unwrap_or_default()
            );
        }
        OutputFormat::Text => {
            println!("Yamlr Forensic Compliance Audit");
            println!("===============================");
            println!("Target:        {}", target);
            println!("Files Scanned: {}", total_files);
            println!("Findings:      {}", total_findings);
            println!("Elapsed Time:  {:.2?}\n", elapsed);

            for f in &findings_report {
                println!(
                    "[{}] {} - {} ({}:{})",
                    f["severity"].as_str().unwrap_or("INFO"),
                    f["rule_id"].as_str().unwrap_or(""),
                    f["title"].as_str().unwrap_or(""),
                    f["file"].as_str().unwrap_or(""),
                    f["line"].as_i64().unwrap_or(0),
                );
                println!("  └─ {}", f["message"].as_str().unwrap_or(""));
            }
        }
    }

    if total_findings > 0 {
        EXIT_VIOLATIONS
    } else {
        EXIT_SUCCESS
    }
}

fn build_audit_sarif(findings: &[serde_json::Value]) -> serde_json::Value {
    let mut rules = BTreeMap::new();
    let results: Vec<serde_json::Value> = findings
        .iter()
        .map(|finding| {
            let rule_id = finding["rule_id"].as_str().unwrap_or("YAMLR-AUDIT");
            let title = finding["title"].as_str().unwrap_or(rule_id);
            let message = finding["message"].as_str().unwrap_or(title);
            let severity = finding["severity"].as_str().unwrap_or("note");
            let level = match severity.to_ascii_lowercase().as_str() {
                "error" | "critical" | "high" => "error",
                "warning" | "medium" => "warning",
                _ => "note",
            };
            let line = finding["line"]
                .as_u64()
                .filter(|line| *line > 0)
                .unwrap_or(1);
            let file = finding["file"].as_str().unwrap_or("");
            let relative_file = crate::path_utils::relativize_to_workspace(file, None);

            rules.entry(rule_id.to_string()).or_insert_with(|| {
                serde_json::json!({
                    "id": rule_id,
                    "shortDescription": { "text": title },
                    "fullDescription": { "text": message },
                    "helpUri": format!("https://yamlr.dev/errors/{}", rule_id.to_lowercase())
                })
            });

            serde_json::json!({
                "ruleId": rule_id,
                "level": level,
                "message": { "text": message },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": { "uri": relative_file },
                        "region": { "startLine": line, "startColumn": 1 }
                    }
                }]
            })
        })
        .collect();

    serde_json::json!({
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "yamlr",
                    "version": "0.1.0",
                    "informationUri": "https://yamlr.dev",
                    "rules": rules.into_values().collect::<Vec<_>>()
                }
            },
            "results": results
        }]
    })
}

fn process_audit_entries<I, F>(entries: I, process_file: &mut F) -> Result<(), String>
where
    I: IntoIterator<Item = Result<walkdir::DirEntry, walkdir::Error>>,
    F: FnMut(&Path) -> Result<(), String>,
{
    for entry in entries {
        let entry = entry.map_err(|error| format!("Failed to traverse audit target: {}", error))?;
        let path = entry.path();
        if path.is_file()
            && path
                .extension()
                .is_some_and(|extension| extension == "yaml" || extension == "yml")
        {
            process_file(path)?;
        }
    }
    Ok(())
}

/// Lists all available forensic detectors, CIS rules, and API deprecations.
///
/// Why: Provides an offline, hermetic reference catalog for compliance auditors
/// and automated tooling to inspect active security rules.
pub fn execute_catalog(args: &[String]) -> i32 {
    let parsed = match parse_catalog_arguments(args) {
        Ok(parsed) => parsed,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let category_filter = parsed
        .get_one::<String>("category")
        .map(|value| value.to_lowercase());
    let format_json = parsed.get_flag("json");

    let catalog = get_catalog();
    let deprecations = get_deprecations();

    if format_json {
        let output = serde_json::json!({
            "catalog_version": catalog.catalog_version,
            "total_detectors": catalog.detectors.len(),
            "total_deprecations": deprecations.apis.len(),
            "detectors": catalog.detectors,
            "deprecations": deprecations.apis,
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&output).unwrap_or_default()
        );
        return EXIT_SUCCESS;
    }

    println!(
        "Yamlr Forensic Rules Catalog (v{})",
        catalog.catalog_version
    );
    println!("=======================================================\n");

    println!(
        "Active Forensic Detectors ({} rules):",
        catalog.detectors.len()
    );
    println!(
        "{:<10} {:<15} {:<10} {:<30}",
        "ID", "CATEGORY", "SEVERITY", "NAME"
    );
    println!("{:-<10} {:-<15} {:-<10} {:-<30}", "", "", "", "");

    for d in &catalog.detectors {
        if let Some(ref cat) = category_filter {
            if !d.category.to_lowercase().contains(cat) {
                continue;
            }
        }
        println!(
            "{:<10} {:<15} {:<10} {:<30}",
            d.id, d.category, d.severity, d.name
        );
    }

    println!(
        "\nKubernetes API Deprecations ({} tracked APIs):",
        deprecations.apis.len()
    );
    for api in deprecations.apis.iter().take(15) {
        println!(
            "  - {} -> {} (removed in v{})",
            api.deprecated_api, api.replacement_api, api.removed_in_version
        );
    }
    if deprecations.apis.len() > 15 {
        println!(
            "  ... and {} more deprecations.",
            deprecations.apis.len() - 15
        );
    }

    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    #[ignore = "Run scripts/ci/verify_report_contracts.py to validate these serializers against OASIS"]
    fn report_contract_fixture_audit() {
        let findings = vec![serde_json::json!({"file": "pod.yaml", "rule_id": "SEC-001",
            "severity": "high", "title": "Privileged workload", "message": "Disable privileged mode", "line": 1})];
        for (name, values) in [
            ("audit-sarif-findings", findings.as_slice()),
            ("audit-sarif-clean", &[]),
        ] {
            println!(
                "YAMLR_REPORT_CONTRACT:{}",
                serde_json::json!({"name": name, "report": build_audit_sarif(values)})
            );
        }
    }

    #[test]
    fn test_catalog_lists_rules_successfully() {
        let args = vec!["yamlr".to_string(), "catalog".to_string()];
        assert_eq!(execute_catalog(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_catalog_json_output() {
        let args = vec![
            "yamlr".to_string(),
            "catalog".to_string(),
            "--json".to_string(),
        ];
        assert_eq!(execute_catalog(&args), EXIT_SUCCESS);
    }

    #[test]
    fn catalog_rejects_unknown_options_and_missing_category_values() {
        for args in [
            vec!["yamlr", "catalog", "--unknown"],
            vec!["yamlr", "catalog", "--category"],
            vec!["yamlr", "catalog", "--category", "--json"],
            vec!["yamlr", "catalog", "--category="],
            vec!["yamlr", "catalog", "--category", "security", "-c", "policy"],
            vec!["yamlr", "catalog", "--json", "-j"],
        ] {
            let args = args.into_iter().map(str::to_string).collect::<Vec<_>>();
            assert_eq!(execute_catalog(&args), EXIT_USAGE, "args: {args:?}");
        }
    }

    #[test]
    fn test_audit_clean_manifest_exits_zero() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("secure_pod.yaml");
        let secure_yaml = r#"
apiVersion: v1
kind: Pod
metadata:
  name: hardened-pod
  namespace: default
spec:
  securityContext:
    runAsNonRoot: true
  containers:
    - name: app
      image: nginx:1.25.3@sha256:0d17b2ec6178a45bb39960efd302e5e1b4f7e527018137c4c00769982a5587aa
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
"#;
        fs::write(&file_path, secure_yaml).unwrap();

        let args = vec![
            "yamlr".to_string(),
            "audit".to_string(),
            file_path.to_str().unwrap().to_string(),
            "--output".to_string(),
            "json".to_string(),
        ];
        assert_eq!(execute_audit(&args), EXIT_SUCCESS);
    }

    #[test]
    fn audit_rejects_unsupported_output_with_usage_exit_code() {
        let args = vec![
            "yamlr".to_string(),
            "audit".to_string(),
            "missing-target.yaml".to_string(),
            "--output".to_string(),
            "xml".to_string(),
        ];

        assert_eq!(execute_audit(&args), EXIT_USAGE);
    }

    #[test]
    fn audit_sarif_output_uses_sarif_2_1_structure_and_severity() {
        let findings = vec![serde_json::json!({
            "file": "manifests/pod.yaml",
            "rule_id": "SEC-001",
            "severity": "HIGH",
            "title": "Privileged container",
            "message": "Container allows privileged execution.",
            "line": 7
        })];

        let report = build_audit_sarif(&findings);

        assert_eq!(report["version"], "2.1.0");
        assert!(report["$schema"]
            .as_str()
            .unwrap()
            .contains("sarif-schema-2.1.0.json"));
        assert_eq!(report["runs"][0]["tool"]["driver"]["name"], "yamlr");
        assert_eq!(
            report["runs"][0]["tool"]["driver"]["rules"][0]["id"],
            "SEC-001"
        );
        assert_eq!(report["runs"][0]["results"][0]["ruleId"], "SEC-001");
        assert_eq!(report["runs"][0]["results"][0]["level"], "error");
        assert_eq!(
            report["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]
                ["startLine"],
            7
        );
    }

    #[test]
    fn audit_single_file_read_failure_returns_system_error() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("invalid-encoding.yaml");
        fs::write(&file_path, [0xff, 0xfe]).unwrap();
        let args = vec![
            "yamlr".to_string(),
            "audit".to_string(),
            file_path.to_str().unwrap().to_string(),
        ];

        assert_eq!(execute_audit(&args), crate::cli::EXIT_SYSTEM_ERROR);
    }

    #[test]
    fn audit_directory_read_failure_returns_system_error() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("invalid-encoding.yaml"), [0xff, 0xfe]).unwrap();
        let args = vec![
            "yamlr".to_string(),
            "audit".to_string(),
            dir.path().to_str().unwrap().to_string(),
        ];

        assert_eq!(execute_audit(&args), crate::cli::EXIT_SYSTEM_ERROR);
    }

    #[test]
    fn audit_propagates_directory_traversal_errors() {
        let dir = tempdir().unwrap();
        let missing = dir.path().join("missing");
        let mut process_file = |_path: &Path| -> Result<(), String> { Ok(()) };

        let error = process_audit_entries(WalkDir::new(missing), &mut process_file).unwrap_err();

        assert!(error.contains("Failed to traverse audit target"));
    }
}

pub(crate) fn parse_audit_arguments(args: &[String]) -> Result<clap::ArgMatches, clap::Error> {
    crate::cli::parse_command_args(
        Command::new("audit")
            .about("Audit manifests for compliance, deprecated APIs, and secret leakage")
            .arg(Arg::new("target").default_value("."))
            .arg(
                Arg::new("output")
                    .long("output")
                    .short('o')
                    .default_value("text")
                    .value_parser(["text", "json", "sarif"]),
            ),
        args,
    )
}

pub(crate) fn parse_catalog_arguments(args: &[String]) -> Result<clap::ArgMatches, clap::Error> {
    crate::cli::parse_command_args(
        Command::new("catalog")
            .about("List compliance detectors and Kubernetes API deprecations")
            .arg(
                Arg::new("category")
                    .long("category")
                    .short('c')
                    .value_parser(clap::builder::NonEmptyStringValueParser::new()),
            )
            .arg(
                Arg::new("json")
                    .long("json")
                    .short('j')
                    .action(ArgAction::SetTrue),
            ),
        args,
    )
}
