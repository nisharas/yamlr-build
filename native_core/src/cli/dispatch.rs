//! Yamlr CLI Dispatch and Command Routing Engine.
//!
//! Why: Centralizes CLI command parsing, flag routing, diagnostic validation,
//! and exit-code semantics to maintain clean separation between the process entry point
//! and command execution logic.

use super::{
    admin_cmd::execute_admin,
    audit_cmd::{execute_audit, execute_catalog},
    baseline_cmd::execute_baseline,
    check_cmd::execute_check,
    completion_cmd::execute_completion,
    demo_cmd::execute_demo,
    diff_viewer::execute_diff,
    dna_cmd::execute_dna,
    doctor_cmd::{execute_diagnose, execute_doctor},
    evidence_cmd::execute_evidence,
    explain_cmd::execute_explain,
    features_cmd::execute_features,
    fleet_cmd::execute_fleet,
    fmt_cmd::{execute_fix, execute_fmt},
    graph_cmd::{execute_drift, execute_graph},
    guide_cmd::execute_guide,
    heal_cmd::execute_heal,
    idp_export_cmd::execute_idp_export,
    init_cmd::execute_init,
    lsp_server::execute_lsp,
    mcp_server::execute_mcp,
    metrics_cmd::execute_metrics,
    rollback_cmd::execute_rollback,
    scan_cmd::execute_scan,
    schema_cmd::execute_schema,
    secure_cmd::execute_secure,
    sign_cmd::{execute_sign, execute_verify},
    status_cmd::execute_status,
    subscription_cmd::{execute_auth, execute_subscription},
    utility_cmds::{
        execute_install, execute_legal, execute_manual, execute_migrate, execute_rules,
        execute_stats, execute_welcome,
    },
    vap_cmd::execute_vap,
    watch::execute_watch,
    webhook_cmd::execute_webhook,
    EXIT_SUCCESS, EXIT_USAGE,
};
use crate::security::{
    renew_team_access_if_due, required_features_for_args, stored_tier, LicenseFeature,
    active_license_public_key,
};

/// Dispatches CLI arguments to the appropriate command handler and returns POSIX exit code.
pub fn run(args: &[String]) -> i32 {
    if args.len() < 2 {
        print_usage();
        return EXIT_SUCCESS;
    }

    let clean_args = args.to_vec();

    let command = if clean_args.len() >= 2 {
        clean_args[1].to_lowercase()
    } else {
        print_usage();
        return EXIT_SUCCESS;
    };

    if let Some(Err(error)) = super::validate_command_arguments(&command, &clean_args) {
        return super::report_argument_error(error);
    }

    for feature in required_features_for_args(&clean_args) {
        let telemetry_suppressed = feature == LicenseFeature::PulseTelemetry
            && !crate::telemetry_gate::is_telemetry_enabled(&clean_args);
        if !telemetry_suppressed {
            if feature != LicenseFeature::PulseTelemetry {
                if let Err(error) = renew_team_access_if_due(active_license_public_key()) {
                    eprintln!("[WARN] Team entitlement renewal could not complete: {error}");
                }
            }
            let tier = stored_tier(active_license_public_key());
            if !tier.includes(feature) {
                let required_tier = if feature == LicenseFeature::PulseTelemetry {
                    "Enterprise"
                } else {
                    "paid"
                };
                eprintln!(
                    "[ERROR] The '{}' command requires the {} tier. Run 'yamlr auth status' for license details.",
                    command, required_tier
                );
                return super::EXIT_VIOLATIONS;
            }
        }
    }

    match command.as_str() {
        "scan" => execute_scan(&clean_args),
        "heal" => execute_heal(&clean_args),
        "diff" => execute_diff(&clean_args),
        "fmt" => execute_fmt(&clean_args),
        "fix" => execute_fix(&clean_args),
        "check" => execute_check(&clean_args),
        "audit" => execute_audit(&clean_args),
        "catalog" => execute_catalog(&clean_args),
        "baseline" => execute_baseline(&clean_args),
        "doctor" => execute_doctor(&clean_args),
        "diagnose" => execute_diagnose(&clean_args),
        "init" => execute_init(&clean_args),
        "dna" => execute_dna(&clean_args),
        "explain" => execute_explain(&clean_args),
        "secure" => execute_secure(&clean_args),
        "fleet" => execute_fleet(&clean_args),
        "lsp" => execute_lsp(),
        "mcp" => execute_mcp(&clean_args),
        "rollback" | "restore" => execute_rollback(&clean_args),
        "sign" => execute_sign(&clean_args),
        "verify" => execute_verify(&clean_args),
        "graph" => execute_graph(&clean_args),
        "drift" => execute_drift(&clean_args),
        "roi" | "impact" | "pulse" | "metrics" => execute_metrics(&clean_args),
        "schema" => execute_schema(&clean_args),
        "admin" => execute_admin(&clean_args),
        "completion" => execute_completion(&clean_args),
        "demo" => execute_demo(&clean_args),
        "features" => execute_features(&clean_args),
        "status" => execute_status(&clean_args),
        "evidence" => execute_evidence(&clean_args),
        "idp-export" => execute_idp_export(&clean_args),
        "auth" => execute_auth(&clean_args),
        "guide" => execute_guide(&clean_args),
        "subscribe" | "upgrade" => execute_subscription(&clean_args),
        "install" => execute_install(&clean_args),
        "legal" => execute_legal(&clean_args),
        "manual" | "man" => execute_manual(&clean_args),
        "migrate" => execute_migrate(&clean_args),
        "rules" => execute_rules(&clean_args),
        "welcome" => execute_welcome(&clean_args),
        "stats" => execute_stats(&clean_args),
        "export-vap" | "vap" => execute_vap(&clean_args),
        "watch" => execute_watch(&clean_args),
        "webhook" => execute_webhook(&clean_args),
        "rpc" | "service" | "daemon" => crate::grpc::execute_rpc_daemon(&clean_args),
        "lint" => execute_scan(&clean_args),
        "version" | "--version" | "-v" => {
            let json_flag = clean_args.iter().any(|a| a == "--json" || a == "-j");
            print_version(json_flag);
            EXIT_SUCCESS
        }
        "help" | "--help" | "-h" => {
            print_usage();
            EXIT_SUCCESS
        }
        _ => {
            eprintln!(
                "[ERROR] Unknown command '{}'. Run 'yamlr help' for usage.",
                command
            );
            EXIT_USAGE
        }
    }
}

pub fn print_usage() {
    println!("Yamlr — The Autonomous Resolution Plane for Kubernetes Manifests");
    println!("\nUSAGE:");
    println!("    yamlr <COMMAND> [OPTIONS] [PATH]");
    println!("\nCORE COMMANDS:");
    println!("    scan     Audit manifests for schema and integrity violations");
    println!("    heal     Safely auto-remediate manifests with comment preservation");
    println!("    diff     Preview unified color diff of proposed remediations");
    println!("    fmt      Canonical formatter (reorder keys to K8s schema standards, -w)");
    println!("    fix      Instant auto-repair (non-destructive schema and deprecation fix)");
    println!("\nGOVERNANCE & TOPOLOGY COMMANDS:");
    println!("    rollback Restore manifests to previous state using atomic WAL journal");
    println!("    sign     Cryptographically sign manifests with HMAC-SHA256");
    println!("    verify   Forensically verify manifest signatures against tampering");
    println!("    graph    Generate directed relational topology dependency graph");
    println!("    drift    Inspect fleet for API version drift and circular loops");
    println!("    roi      Calculate engineering hours saved and blast radius metrics");
    println!("    dna      Generate cryptographic structural DNA fingerprint of manifests");
    println!("    fleet    Multi-repository GitOps batch remediation and PR opening");
    println!("    vap      Export or ingest K8s 1.30+ ValidatingAdmissionPolicy manifests");
    println!("\nINTEGRATION & DAEMON COMMANDS:");
    println!("    lsp      Run Language Server Protocol (stdio JSON-RPC daemon)");
    println!("    mcp      Run Model Context Protocol server for AI coding agents");
    println!("    rpc      Inspect RPC configuration (network listener is not implemented)");
    println!("    webhook  Run in-cluster admission controller daemon (validating/mutating)");
    println!("    watch    Continuous filesystem watcher triggering instant incremental scans");
    println!("    schema   Ingest and manage external CRD schema definitions");
    println!("    doctor   Validate native engine integrity and loaded schemas");
    println!("    status   Display system diagnostics, license tier, and engine health");
    println!("    install  Install pre-commit hooks and developer workflows");
    println!("    auth     Manage license activation and air-gapped tokens");
    println!("    version  Display binary version and architecture (--json for structured output)");
    println!("\nOPTIONS:");
    println!("    -k, --k8s-version <VER> Target Kubernetes version (default: 1.30)");
    println!("    -o, --output <FMT>      Output format: text, json, sarif");
    println!("    -a, --apply             Write healed manifests to disk");
    println!("    -d, --dry-run           Preview healed manifests without modifying files");
    println!("    --diff                  Display unified color diff of proposed changes");
    println!("    --fail-on <SEV>         Exit with non-zero code on error, warning, or note");
    println!("    --exit-zero             Always exit with code 0 (for non-blocking CI warnings)");
    println!("    --otel, --export-metrics Export OpenTelemetry Prometheus exposition metrics");
    println!("    --push-telemetry        Explicitly send an Enterprise scan-completion event");
    println!(
        "    --no-telemetry          Disable all telemetry collection (air-gapped compliance)"
    );
    println!("    -h, --help              Print help information");
}

pub fn print_version(json: bool) {
    if json {
        // Why: Structured JSON version output for GitHub Actions matrix, CI toolchain
        // integration, and programmatic capability detection. Avoids screen-scraping
        // brittle human-readable text for automated workflows.
        let version_info = serde_json::json!({
            "version": env!("CARGO_PKG_VERSION"),
            "engine": "borrowed-document-slice-streaming",
            "schemas": "embedded-openapi-v3",
            "platform": std::env::consts::OS,
            "arch": std::env::consts::ARCH,
            "status": "production"
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&version_info).unwrap_or_default()
        );
    } else {
        println!(
            "yamlr v{} (Rust Native Standalone Core)",
            env!("CARGO_PKG_VERSION")
        );
        println!("Author: Yamlr Team <team@yamlr.dev>");
        println!("Engine: Borrowed Document-Slice Streaming, Embedded OpenAPI v3 Schemas");
        println!("Status: Production-Grade Autonomous Resolution Engine");
    }
}

pub fn run_doctor() {
    execute_doctor(&["yamlr".to_string(), "doctor".to_string()]);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dispatch_empty_args_shows_help() {
        let args = vec!["yamlr".to_string()];
        assert_eq!(run(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_dispatch_help_flags() {
        assert_eq!(
            run(&["yamlr".to_string(), "help".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "--help".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(run(&["yamlr".to_string(), "-h".to_string()]), EXIT_SUCCESS);
    }

    #[test]
    fn test_dispatch_version_flags() {
        assert_eq!(
            run(&["yamlr".to_string(), "version".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "--version".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(run(&["yamlr".to_string(), "-v".to_string()]), EXIT_SUCCESS);
    }

    #[test]
    fn test_dispatch_version_json_flag() {
        // Why: Verifies that `yamlr version --json` routes correctly and returns EXIT_SUCCESS.
        // The --json flag enables programmatic toolchain integration (GitHub Actions, CI scripts).
        assert_eq!(
            run(&[
                "yamlr".to_string(),
                "version".to_string(),
                "--json".to_string()
            ]),
            EXIT_SUCCESS
        );
    }

    #[test]
    fn test_dispatch_doctor() {
        assert_eq!(
            run(&["yamlr".to_string(), "doctor".to_string()]),
            EXIT_SUCCESS
        );
    }

    #[test]
    fn test_dispatch_phase4_commands() {
        assert_eq!(
            run(&["yamlr".to_string(), "catalog".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "features".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "status".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "welcome".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "install".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "legal".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "manual".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "migrate".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "rules".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&[
                "yamlr".to_string(),
                "completion".to_string(),
                "bash".to_string()
            ]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "demo".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&["yamlr".to_string(), "guide".to_string()]),
            EXIT_SUCCESS
        );
        assert_eq!(
            run(&[
                "yamlr".to_string(),
                "auth".to_string(),
                "status".to_string()
            ]),
            EXIT_SUCCESS
        );
    }

    #[test]
    fn test_dispatch_auth_activate() {
        let code = run(&[
            "yamlr".to_string(),
            "auth".to_string(),
            "activate".to_string(),
            "YAMLR-PRO-ENTERPRISE-KEY-ONLINE-VAL".to_string(),
        ]);
        assert_eq!(code, crate::cli::EXIT_VIOLATIONS);
    }

    #[test]
    fn test_dispatch_lint_alias() {
        // lint routes to execute_scan, should succeed on current dir
        let code = run(&["yamlr".to_string(), "lint".to_string(), ".".to_string()]);
        assert_eq!(code, EXIT_SUCCESS);
    }

    #[test]
    fn test_dispatch_watch_invalid_path() {
        let code = run(&[
            "yamlr".to_string(),
            "watch".to_string(),
            "path/that/does/not/exist/xyz".to_string(),
        ]);
        assert_eq!(code, EXIT_USAGE);
    }

    #[test]
    fn test_dispatch_unknown_command() {
        let code = run(&["yamlr".to_string(), "nonexistent-cmd-xyz".to_string()]);
        assert_eq!(code, EXIT_USAGE);
    }

    #[test]
    fn test_dispatch_webhook_dry_run() {
        let code = run(&[
            "yamlr".to_string(),
            "webhook".to_string(),
            "--dry-run".to_string(),
        ]);
        assert_eq!(code, EXIT_SUCCESS);
    }

    #[test]
    fn test_dispatch_rejects_unimplemented_json_log_flag() {
        let code = run(&[
            "yamlr".to_string(),
            "scan".to_string(),
            ".".to_string(),
            "--json-log".to_string(),
        ]);
        assert_eq!(code, crate::cli::EXIT_USAGE);
    }

    #[test]
    fn parser_help_is_successful_without_paid_feature_activation() {
        for command in [
            "scan", "lint", "heal", "check", "diff", "schema", "explain", "audit", "catalog",
            "baseline", "fmt", "fix",
        ] {
            assert_eq!(
                run(&["yamlr".into(), command.into(), "--help".into()]),
                EXIT_SUCCESS
            );
        }
    }
}
