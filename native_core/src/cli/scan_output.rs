//! Scan command status output and quiet-mode handling.

use super::ViolationRecord;
use crate::cli::{get_flag_value, OutputFormat};
use std::fmt::Arguments;

pub(super) fn quiet_requested(args: &[String]) -> bool {
    args.iter().any(|arg| arg == "--quiet" || arg == "-q")
}

pub(super) fn status(args: &[String], message: Arguments<'_>) {
    if !quiet_requested(args) {
        eprintln!("{message}");
    }
}

pub(super) fn oci_reference(
    args: &[String],
    target: &str,
    registry: &str,
    repository: &str,
    tag: Option<&str>,
    digest: Option<&str>,
) {
    if quiet_requested(args) {
        return;
    }

    eprintln!("[OCI] Detected OCI chart URI: {}", target);
    eprintln!("[OCI] Live registry retrieval is not available in this build. Provide a local");
    eprintln!("[OCI]       chart content layer via --oci-layer <path> to scan its templates.");
    eprintln!("[OCI] Registry:    {}", registry);
    eprintln!("[OCI] Repository:  {}", repository);
    if let Some(tag) = tag {
        eprintln!("[OCI] Tag:         {}", tag);
    }
    if let Some(digest) = digest {
        eprintln!("[OCI] Digest:      {}", digest);
    }
}

pub(super) fn render_violations(results: &[ViolationRecord]) -> String {
    let mut output = String::new();
    for result in results {
        output.push_str(&format!(
            "{} {} {}:{} {}\n",
            result.severity.to_uppercase(),
            result.rule_id,
            result.file,
            result.line,
            result.message
        ));
    }
    output
}

/// An incomplete scan emits an explicit error report, replacing any previous
/// report at the requested output path. Partial findings are never labelled
/// as a successful scan. The caller retains the original nonzero exit code.
pub(super) fn report_failure(args: &[String], target: &str, message: &str) {
    let format = get_flag_value(args, "--output")
        .and_then(|value| OutputFormat::parse(&value))
        .unwrap_or_else(|| {
            if args.iter().any(|arg| arg == "--sarif") {
                OutputFormat::Sarif
            } else if args.iter().any(|arg| arg == "--json") {
                OutputFormat::Json
            } else {
                OutputFormat::Text
            }
        });
    if format == OutputFormat::Text {
        return;
    }
    let report = failure_report(&format, target, message);
    let report = serde_json::to_string_pretty(&report).expect("JSON value serialization");
    if let Some(path) = get_flag_value(args, "--output-file") {
        if let Err(error) = std::fs::write(&path, report) {
            eprintln!(
                "[ERROR] Failed to write incomplete-scan report '{}': {}",
                path, error
            );
        }
    } else {
        println!("{report}");
    }
}

pub(super) fn failure_report(
    format: &OutputFormat,
    target: &str,
    message: &str,
) -> serde_json::Value {
    if *format == OutputFormat::Sarif {
        serde_json::json!({
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {"name": "Yamlr", "version": env!("CARGO_PKG_VERSION")}},
                "results": [],
                "invocations": [{
                    "executionSuccessful": false,
                    "toolExecutionNotifications": [{"level": "error", "message": {"text": message}}]
                }],
                "properties": {"target": target, "complete": false}
            }]
        })
    } else {
        serde_json::json!({
            "status": "error", "complete": false,
            "errors": [{"target": target, "message": message}]
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn quiet_flag_and_short_alias_are_recognized() {
        assert!(quiet_requested(&[
            "yamlr".into(),
            "scan".into(),
            "--quiet".into()
        ]));
        assert!(quiet_requested(&[
            "yamlr".into(),
            "scan".into(),
            "-q".into()
        ]));
    }

    #[test]
    fn quiet_mode_is_disabled_without_the_flag() {
        assert!(!quiet_requested(&["yamlr".into(), "scan".into()]));
    }

    #[test]
    fn quiet_report_contains_only_violation_details() {
        let results = vec![ViolationRecord {
            file: "deploy.yaml".into(),
            check_type: "schema".into(),
            rule_id: "SCH-001".into(),
            message: "spec.replicas: required field is missing".into(),
            severity: "error".into(),
            line: 4,
        }];

        assert_eq!(
            render_violations(&results),
            "ERROR SCH-001 deploy.yaml:4 spec.replicas: required field is missing\n"
        );
        assert!(render_violations(&[]).is_empty());
    }

    #[test]
    fn incomplete_scan_report_does_not_claim_a_clean_scan() {
        let report = failure_report(
            &OutputFormat::Json,
            "manifests",
            "cannot read manifests/pod.yaml",
        );
        assert_eq!(report["status"], "error");
        assert_eq!(report["complete"], false);
        assert_eq!(
            report["errors"][0]["message"],
            "cannot read manifests/pod.yaml"
        );
        assert!(report.get("results").is_none());
        let report = failure_report(&OutputFormat::Sarif, "manifests", "permission denied");
        assert_eq!(
            report["runs"][0]["invocations"][0]["executionSuccessful"],
            false
        );
        assert_eq!(
            report["runs"][0]["invocations"][0]["toolExecutionNotifications"][0]["level"],
            "error"
        );
    }
}
