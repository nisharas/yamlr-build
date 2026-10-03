//! Unit tests for yamlr native scan CLI command.
//!
//! Why: Extracted to a discrete test module to maintain the < 500-line modularity
//! guardrail on scan_cmd.rs, enabling clean separation of test setup and verification logic.

use super::*;
use flate2::write::GzEncoder;
use flate2::Compression;
use std::io::Cursor;
use tar::Builder;
use tempfile::tempdir;

#[test]
fn helm_watch_tracks_template_file_extensions() {
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        "--helm".to_string(),
    ];

    assert_eq!(scan_watch_extensions(&args), &["yaml", "yml", "tpl"]);
}

#[test]
fn scan_target_resolver_keeps_stdin_marker_as_positional_input() {
    let args = vec!["yamlr".to_string(), "scan".to_string(), "-".to_string()];

    assert_eq!(
        parse_scan_arguments(&args)
            .unwrap()
            .get_one::<String>("target")
            .unwrap(),
        "-"
    );
}

#[test]
fn scan_argument_contract_accepts_options_before_and_after_target() {
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        "--output".to_string(),
        "json".to_string(),
        "manifests".to_string(),
        "--fail-on=warning".to_string(),
    ];

    assert!(validate_scan_arguments(&args).is_ok());
}

#[test]
fn compact_scan_options_control_the_actual_report_and_target() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("config.yaml");
    fs::write(&manifest, "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: compact-flags\ndata:\n  setting: enabled\n").unwrap();
    let output = dir.path().join("report.json");
    let args = vec![
        "yamlr".into(),
        "scan".into(),
        "-ojson".into(),
        "-k1.30".into(),
        "-q".into(),
        format!("-f{}", output.display()),
        manifest.to_str().unwrap().into(),
    ];
    assert_eq!(execute_scan(&args), EXIT_SUCCESS);
    let report: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(output).unwrap()).unwrap();
    assert_eq!(report["total_files"], 1);
    assert_eq!(report["status"], "passed");
    assert_eq!(report["results"], serde_json::json!([]));
}

#[test]
fn scan_target_after_terminator_is_never_interpreted_as_an_option() {
    let args = ["yamlr", "scan", "--json", "--", "--helm"].map(str::to_string);
    let parsed = parse_scan_arguments(&args).unwrap();
    assert_eq!(parsed.get_one::<String>("target").unwrap(), "--helm");
    assert!(!parsed.get_flag("helm"));
    assert_eq!(
        normalize_scan_options(&parsed),
        vec!["yamlr", "scan", "--json"]
    );
}

#[test]
fn failed_reads_replace_stale_success_reports_even_with_exit_zero() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("invalid-encoding.yaml");
    fs::write(&manifest, [0xff, 0xfe]).unwrap();
    for format in ["json", "sarif"] {
        let output = dir.path().join(format!("report.{format}"));
        fs::write(&output, "{\"status\":\"passed\"}").unwrap();
        let args = vec![
            "yamlr".into(),
            "scan".into(),
            manifest.to_str().unwrap().into(),
            "--output".into(),
            format.into(),
            "--output-file".into(),
            output.to_str().unwrap().into(),
            "--exit-zero".into(),
        ];
        assert_eq!(execute_scan(&args), crate::cli::EXIT_SYNTAX_ERROR);
        let report: serde_json::Value =
            serde_json::from_str(&fs::read_to_string(output).unwrap()).unwrap();
        if format == "json" {
            assert_eq!(report["status"], "error");
            assert_eq!(report["complete"], false);
            assert!(report["errors"][0]["message"]
                .as_str()
                .unwrap()
                .contains("invalid-encoding.yaml"));
        } else {
            assert_eq!(
                report["runs"][0]["invocations"][0]["executionSuccessful"],
                false
            );
            assert_eq!(report["runs"][0]["properties"]["complete"], false);
        }
    }
}

#[test]
fn scan_argument_contract_rejects_unknown_options_missing_values_and_duplicates() {
    for tail in [
        vec!["--surprise".to_string()],
        vec!["--output".to_string()],
        vec![
            "--crd".to_string(),
            "schema.yaml".to_string(),
            "--crd".to_string(),
            "other.yaml".to_string(),
        ],
        vec![
            "--output".to_string(),
            "json".to_string(),
            "-o".to_string(),
            "text".to_string(),
        ],
    ] {
        let mut args = vec!["yamlr".to_string(), "scan".to_string()];
        args.extend(tail);
        assert!(
            validate_scan_arguments(&args).is_err(),
            "accepted invalid args: {args:?}"
        );
    }
}

#[test]
fn kube_version_alias_selects_the_requested_scan_schema() {
    for args in [
        vec![
            "yamlr".to_string(),
            "scan".to_string(),
            "--kube-version".to_string(),
            "1.31".to_string(),
        ],
        vec![
            "yamlr".to_string(),
            "scan".to_string(),
            "--kube-version=1.31".to_string(),
        ],
    ] {
        assert_eq!(selected_k8s_version(&args), "1.31");
    }
}

#[test]
fn report_output_write_failure_returns_system_error() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("pod.yaml");
    fs::write(
        &manifest,
        "apiVersion: v1\nkind: Pod\nmetadata:\n  name: sample\n",
    )
    .unwrap();
    let output = dir.path().join("missing").join("report.json");
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        manifest.to_str().unwrap().to_string(),
        "--output".to_string(),
        "json".to_string(),
        "--output-file".to_string(),
        output.to_str().unwrap().to_string(),
    ];

    assert_eq!(execute_scan(&args), crate::cli::EXIT_SYSTEM_ERROR);
}

#[test]
fn scan_rejects_unsupported_output_format_before_processing_the_target() {
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        "missing-target.yaml".to_string(),
        "--output".to_string(),
        "xml".to_string(),
    ];

    assert_eq!(execute_scan(&args), crate::cli::EXIT_USAGE);
}

#[test]
fn scan_rejects_unimplemented_json_log_option() {
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        "--json-log".to_string(),
    ];

    assert_eq!(execute_scan(&args), crate::cli::EXIT_USAGE);
}

#[test]
fn schema_findings_report_the_source_line() {
    let content = "apiVersion: example.test/v1\nkind: Widget\nmetadata:\n  name: sample\ntarget: \"not-a-number\"\n";
    let schemas = [crate::models::NativeSchema {
        kind: "Widget".to_string(),
        api_version: "example.test/v1".to_string(),
        properties: vec![crate::models::SchemaProperty {
            name: "target".to_string(),
            prop_type: "integer".to_string(),
            required: false,
            description: String::new(),
            enum_values: Vec::new(),
        }],
    }];
    let mut total_violations = 0;
    let mut total_integrity = 0;
    let mut results = Vec::new();

    process_manifest_string(
        content,
        "widget.yaml",
        &schemas,
        &mut total_violations,
        &mut total_integrity,
        &mut results,
    )
    .unwrap();

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].line, 5);
}

#[test]
fn duplicate_key_findings_report_the_duplicate_line() {
    let content = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: first\n  name: second\n";
    let mut total_violations = 0;
    let mut total_integrity = 0;
    let mut results = Vec::new();

    process_manifest_string(
        content,
        "pod.yaml",
        &[],
        &mut total_violations,
        &mut total_integrity,
        &mut results,
    )
    .unwrap();

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].line, 5);
}

#[test]
fn scan_fails_when_document_limit_would_make_the_report_incomplete() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("too-many-documents.yaml");
    let content = format!("kind: Pod\n{}", "---\nkind: Pod\n".repeat(1000));
    fs::write(&manifest, content).unwrap();
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        manifest.to_str().unwrap().to_string(),
    ];

    assert_eq!(execute_scan(&args), 2);
}

fn make_oci_layer(path: &str, content: &str) -> Vec<u8> {
    let encoder = GzEncoder::new(Vec::new(), Compression::fast());
    let mut archive = Builder::new(encoder);
    let bytes = content.as_bytes();
    let mut header = tar::Header::new_gnu();
    header.set_path(path).unwrap();
    header.set_size(bytes.len() as u64);
    header.set_mode(0o644);
    header.set_cksum();
    archive.append(&header, Cursor::new(bytes)).unwrap();
    archive.into_inner().unwrap().finish().unwrap()
}

#[test]
fn test_scan_cmd_output_file_writing() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("pod.yaml");
    fs::write(&manifest, "apiVersion: v1\nkind: Pod\nmetadata:\n  name: my-pod\nspec:\n  containers:\n    - name: c\n      image: nginx\n").unwrap();

    let out_file = dir.path().join("report.sarif");
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        manifest.to_str().unwrap().to_string(),
        "--sarif".to_string(),
        "-f".to_string(),
        out_file.to_str().unwrap().to_string(),
        "--exit-zero".to_string(),
    ];

    let exit_code = execute_scan(&args);
    assert_eq!(exit_code, EXIT_SUCCESS);
    assert!(out_file.exists());
    let content = fs::read_to_string(&out_file).unwrap();
    assert!(content.contains("sarif-schema-2.1.0.json"));
}

#[test]
fn test_scan_cmd_kustomize_flag() {
    let dir = tempdir().unwrap();
    let kustomization = r#"
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namePrefix: prod-
resources:
  - app.yaml
"#;
    let app = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 1
"#;
    fs::write(dir.path().join("kustomization.yaml"), kustomization).unwrap();
    fs::write(dir.path().join("app.yaml"), app).unwrap();

    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        dir.path().to_str().unwrap().to_string(),
        "--kustomize".to_string(),
        "--exit-zero".to_string(),
    ];

    let exit_code = execute_scan(&args);
    assert_eq!(exit_code, EXIT_SUCCESS);
}

#[test]
fn test_scan_cmd_oci_uri_without_chart_content_fails() {
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        "oci://ghcr.io/helm-charts/nginx:1.2.3".to_string(),
        "--exit-zero".to_string(),
    ];
    let exit_code = execute_scan(&args);
    assert_eq!(exit_code, 2);
}

#[test]
fn test_scan_cmd_oci_layer_scans_extracted_templates() {
    let dir = tempdir().unwrap();
    let layer_path = dir.path().join("chart.tgz");
    let report_path = dir.path().join("report.json");
    let template = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: oci-test\n";
    fs::write(
        &layer_path,
        make_oci_layer("chart/templates/pod.yaml", template),
    )
    .unwrap();

    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        "--oci-layer".to_string(),
        layer_path.to_str().unwrap().to_string(),
        "--json".to_string(),
        "--output-file".to_string(),
        report_path.to_str().unwrap().to_string(),
    ];

    assert_eq!(execute_scan(&args), EXIT_VIOLATIONS);
    let report: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(report_path).unwrap()).unwrap();
    assert_eq!(report["total_files"], 1);
    assert!(report["schema_violations"].as_u64().unwrap() > 0);
    assert_eq!(report["results"][0]["file"], layer_path.to_str().unwrap());
}

#[test]
fn test_scan_fail_on_applies_to_schema_finding_severity() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("medium-severity.yaml");
    let report_path = dir.path().join("report.json");
    fs::write(
        &manifest,
        "apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n",
    )
    .unwrap();
    let mut args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        manifest.to_str().unwrap().to_string(),
        "--fail-on".to_string(),
        "error".to_string(),
        "--json".to_string(),
        "--output-file".to_string(),
        report_path.to_str().unwrap().to_string(),
    ];

    assert_eq!(execute_scan(&args), EXIT_VIOLATIONS);
    let report: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&report_path).unwrap()).unwrap();
    assert_eq!(report["results"][0]["severity"], "high");

    args[4] = "warning".to_string();
    assert_eq!(execute_scan(&args), EXIT_VIOLATIONS);

    args[4] = "unknown".to_string();
    assert_eq!(execute_scan(&args), crate::cli::EXIT_USAGE);
}

#[test]
fn test_scan_crd_applies_custom_schema_and_does_not_reuse_non_crd_cache() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("widget.yaml");
    let crd = dir.path().join("widget-crd.yaml");
    let report = dir.path().join("report.json");
    fs::write(
        &manifest,
        "apiVersion: example.test/v1\nkind: Widget\nmetadata:\n  name: sample\n",
    )
    .unwrap();
    fs::write(
        &crd,
        "apiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\nmetadata:\n  name: widgets.example.test\nspec:\n  group: example.test\n  names:\n    kind: Widget\n  versions:\n    - name: v1\n      schema:\n        openAPIV3Schema:\n          type: object\n          required: [spec]\n          properties:\n            spec:\n              type: object\n",
    )
    .unwrap();

    let base_args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        manifest.to_str().unwrap().to_string(),
        "--output".to_string(),
        "json".to_string(),
        "--output-file".to_string(),
        report.to_str().unwrap().to_string(),
    ];
    assert_eq!(crate::cli::dispatch::run(&base_args), EXIT_SUCCESS);

    let mut crd_args = base_args;
    crd_args.extend(["--crd".to_string(), crd.to_str().unwrap().to_string()]);
    assert_eq!(crate::cli::dispatch::run(&crd_args), EXIT_VIOLATIONS);

    let report: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(report).unwrap()).unwrap();
    assert_eq!(report["schema_violations"], 1);
    assert!(report["results"][0]["message"]
        .as_str()
        .unwrap()
        .contains("Missing required field 'spec'"));
}

#[test]
fn test_scan_crd_requires_a_valid_input_path() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("widget.yaml");
    fs::write(&manifest, "apiVersion: example.test/v1\nkind: Widget\n").unwrap();
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        manifest.to_str().unwrap().to_string(),
        "--crd".to_string(),
    ];

    assert_eq!(execute_scan(&args), crate::cli::EXIT_USAGE);
}

#[test]
fn unreadable_single_manifest_fails_even_when_exit_zero_is_requested() {
    let dir = tempdir().unwrap();
    let manifest = dir.path().join("invalid-encoding.yaml");
    fs::write(&manifest, [0xff, 0xfe]).unwrap();
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        manifest.to_str().unwrap().to_string(),
        "--exit-zero".to_string(),
    ];

    assert_eq!(execute_scan(&args), 2);
}

#[test]
fn unreadable_manifest_in_directory_fails_the_scan() {
    let dir = tempdir().unwrap();
    fs::write(dir.path().join("invalid-encoding.yaml"), [0xff, 0xfe]).unwrap();
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        dir.path().to_str().unwrap().to_string(),
    ];

    assert_eq!(execute_scan(&args), 2);
}

#[test]
fn unreadable_helm_template_fails_the_chart_scan() {
    let dir = tempdir().unwrap();
    let templates = dir.path().join("templates");
    fs::create_dir_all(&templates).unwrap();
    fs::write(templates.join("invalid-encoding.yaml"), [0xff, 0xfe]).unwrap();
    let args = vec![
        "yamlr".to_string(),
        "scan".to_string(),
        dir.path().to_str().unwrap().to_string(),
        "--helm".to_string(),
    ];

    assert_eq!(execute_scan(&args), 2);
}
#[test]
#[ignore = "Run scripts/ci/verify_report_contracts.py to validate these serializers against OASIS"]
fn report_contract_fixture_scan() {
    let records = vec![super::ViolationRecord {
        file: "manifests/pod.yaml".into(),
        check_type: "integrity".into(),
        rule_id: "REF-001".into(),
        message: "Service selector does not match a workload".into(),
        severity: "high".into(),
        line: 3,
    }];
    for (name, payload) in [
        (
            "scan-sarif-findings",
            serde_json::from_str::<serde_json::Value>(&super::render_sarif("1.30", &records))
                .unwrap(),
        ),
        (
            "scan-sarif-clean",
            serde_json::from_str(&super::render_sarif("1.30", &[])).unwrap(),
        ),
        (
            "scan-sarif-failure",
            super::scan_output::failure_report(
                &crate::cli::OutputFormat::Sarif,
                "pod.yaml",
                "Read failed",
            ),
        ),
    ] {
        println!(
            "YAMLR_REPORT_CONTRACT:{}",
            serde_json::json!({"name": name, "report": payload})
        );
    }
}
