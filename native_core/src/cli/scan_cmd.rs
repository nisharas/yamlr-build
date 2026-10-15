//! High-speed manifest scanning CLI handler in native Rust.

use crate::cli::{get_flag_value, OutputFormat, EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_VIOLATIONS};
use crate::models::NativeSchema;
#[allow(unused_imports)]
pub(crate) use crate::cli::scan_args::{normalize_scan_options, parse_scan_arguments, scan_command};
#[cfg(test)]
pub(crate) use crate::cli::scan_args::validate_scan_arguments;
pub(crate) use crate::cli::scan_render::{render_json, render_sarif, render_text};
use std::{fs, path::Path, time::Instant};

#[path = "scan_crd.rs"]
mod scan_crd;
#[path = "scan_fail_on.rs"]
pub(crate) mod scan_fail_on;
#[path = "scan_file.rs"]
mod scan_file;
#[path = "scan_input.rs"]
mod scan_input;
#[path = "scan_manifest.rs"]
mod scan_manifest;
#[path = "scan_oci.rs"]
mod scan_oci;
#[path = "scan_output.rs"]
mod scan_output;
#[path = "scan_stdin.rs"]
mod scan_stdin;
#[path = "scan_walk.rs"]
mod scan_walk;
pub fn execute_scan(args: &[String]) -> i32 {
    let parsed = match parse_scan_arguments(args) {
        Ok(parsed) => parsed,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target = parsed
        .get_one::<String>("target")
        .or_else(|| parsed.get_one::<String>("oci-layer"))
        .map(String::as_str)
        .unwrap_or(".");
    // Existing execution adapters receive canonical options from Clap, never
    // raw user tokens. Compact flags, aliases, and '=' values thus mean the
    // same thing at validation and execution. The target is passed separately.
    let normalized = normalize_scan_options(&parsed);
    let args = normalized.as_slice();

    let is_watch = args.iter().any(|a| a == "-w" || a == "--watch");
    if is_watch {
        scan_output::status(
            args,
            format_args!(
                "[WATCH] Monitoring '{}' for manifest changes (Ctrl+C to exit)...",
                target
            ),
        );
        let path = Path::new(target);
        let watch_extensions = scan_watch_extensions(args);
        crate::cli::watch::run_watch_loop_checked_with_extensions(
            path,
            None,
            watch_extensions,
            |_| {
                run_single_scan(args, target);
            },
        )
    } else {
        run_single_scan(args, target)
    }
}



pub fn run_single_scan(args: &[String], target: &str) -> i32 {
    let start_time = Instant::now();

    let k8s_version = selected_k8s_version(args);
    if let Err(error) = crate::schemas::validate_k8s_version(&k8s_version) {
        eprintln!("[ERROR] {}", error);
        return crate::cli::EXIT_USAGE;
    }

    let format_str = get_flag_value(args, "--output")
        .or_else(|| get_flag_value(args, "-o"))
        .unwrap_or_else(|| {
            if args.iter().any(|a| a == "--sarif") {
                "sarif".to_string()
            } else if args.iter().any(|a| a == "--json" || a == "-j") {
                "json".to_string()
            } else {
                "text".to_string()
            }
        });

    let format = match OutputFormat::parse(&format_str) {
        Some(format) => format,
        None => {
            eprintln!(
                "[ERROR] Unsupported --output value '{}'. Use text, json, or sarif.",
                format_str
            );
            return crate::cli::EXIT_USAGE;
        }
    };
    let quiet = scan_output::quiet_requested(args);
    let (schemas, crd_cache_context) = match scan_crd::load_scan_schemas(args, &k8s_version) {
        Ok(loaded) => loaded,
        Err(error) => {
            eprintln!("[ERROR] {}", error);
            scan_output::report_failure(args, target, &error);
            return 2;
        }
    };

    let scan_cache_version = match scan_crd::cache_version(&crd_cache_context, &schemas) {
        Ok(version) => version,
        Err(error) => {
            eprintln!("[ERROR] {error}");
            scan_output::report_failure(args, target, &error);
            return EXIT_SYSTEM_ERROR;
        }
    };

    let is_helm = args.iter().any(|a| a == "--helm");
    let is_kustomize = args.iter().any(|a| a == "--kustomize");
    let output_file = get_flag_value(args, "--output-file").or_else(|| get_flag_value(args, "-f"));
    let fail_on_value = get_flag_value(args, "--fail-on").unwrap_or_else(|| "error".to_string());
    let fail_on = match scan_fail_on::FailOn::parse(&fail_on_value) {
        Some(threshold) => threshold,
        None => {
            eprintln!("[ERROR] Unsupported --fail-on value '{}'. Use error, warning, note, any, info, or none.", fail_on_value);
            return crate::cli::EXIT_USAGE;
        }
    };

    let mut total_files = 0;
    let mut total_violations = 0;
    let mut total_integrity = 0;

    let path = Path::new(target);
    let mut results = Vec::new();

    if is_kustomize && path.is_dir() {
        match crate::parsers::kustomize::render_kustomize_directory(path) {
            Ok(rendered) => {
                total_files += 1;
                if let Err(error) = process_manifest_string(
                    &rendered,
                    "kustomization-rendered.yaml",
                    &schemas,
                    &mut total_violations,
                    &mut total_integrity,
                    &mut results,
                ) {
                    eprintln!("[ERROR] Kustomize scan incomplete: {}", error);
                    scan_output::report_failure(args, target, &error.to_string());
                    return 2;
                }
            }
            Err(e) => {
                eprintln!("[ERROR] Kustomize rendering failed: {}", e);
                scan_output::report_failure(args, target, &e.to_string());
                return 2;
            }
        }
    } else if is_helm && path.is_dir() {
        let values_p = path.join("values.yaml");
        if values_p.is_file() {
            total_files += 1;
            if let Err(error) = scan_file::process_file_with_precomputed_cache_version(
                &values_p,
                &schemas,
                &mut total_violations,
                &mut total_integrity,
                &mut results,
                &k8s_version,
                &scan_cache_version,
            ) {
                eprintln!("[ERROR] Helm scan incomplete: {}", error);
                scan_output::report_failure(args, target, &error.to_string());
                return error.exit_code();
            }
        }
        let tpl_dir = path.join("templates");
        if tpl_dir.is_dir() {
            let scan_result =
                scan_walk::visit_matching_files(&tpl_dir, &["yaml", "yml", "tpl"], |file| {
                    total_files += 1;
                    scan_file::process_file_with_precomputed_cache_version(
                        file,
                        &schemas,
                        &mut total_violations,
                        &mut total_integrity,
                        &mut results,
                        &k8s_version,
                        &scan_cache_version,
                    )
                });
            if let Err(error) = scan_result {
                eprintln!("[ERROR] Helm template scan incomplete: {}", error);
                scan_output::report_failure(args, target, &error.to_string());
                return error.exit_code();
            }
        }
    } else if let Some(layer_path) = get_flag_value(args, "--oci-layer") {
        let contents = match scan_oci::load_chart_layer(&layer_path) {
            Ok(contents) => contents,
            Err(e) => {
                eprintln!("[ERROR] {}", e);
                scan_output::report_failure(args, target, &e.to_string());
                return e.exit_code();
            }
        };
        let chart_name = contents
            .chart_name
            .as_deref()
            .map(|name| format!(" '{}'", name))
            .unwrap_or_default();
        scan_output::status(
            args,
            format_args!("[OCI] Scanning Helm chart layer{}.", chart_name),
        );
        total_files += 1;
        if let Err(error) = process_manifest_string(
            &contents.templates_yaml,
            &layer_path,
            &schemas,
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        ) {
            eprintln!("[ERROR] OCI layer scan incomplete: {}", error);
            scan_output::report_failure(args, target, &error.to_string());
            return 2;
        }
    } else if crate::parsers::helm::is_oci_uri(target) {
        match crate::parsers::helm::parse_oci_uri(target) {
            Ok(ref_parts) => {
                scan_output::oci_reference(
                    args,
                    target,
                    &ref_parts.registry,
                    &ref_parts.repository,
                    ref_parts.tag.as_deref(),
                    ref_parts.digest.as_deref(),
                );
                eprintln!(
                    "[ERROR] OCI reference parsed, but no chart content was scanned. Download the Helm chart layer and pass it with --oci-layer <path>."
                );
                scan_output::report_failure(args, target, "Remote OCI retrieval is unavailable; no chart content was scanned. Provide --oci-layer <path>.");
                return 2;
            }
            Err(e) => {
                eprintln!("[ERROR] Invalid OCI URI '{}': {}", target, e);
                scan_output::report_failure(args, target, &e.to_string());
                return 2;
            }
        }
    } else if target == "-" {
        let mut stdin = std::io::stdin();
        if let Err(error) = scan_stdin::process_stdin(
            &mut stdin,
            &schemas,
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        ) {
            eprintln!("[ERROR] Stdin scan incomplete: {}", error);
            scan_output::report_failure(args, target, &error.to_string());
            return error.exit_code();
        }
        total_files += 1;
    } else if path.is_file() {
        if let Err(error) = scan_file::process_file_with_precomputed_cache_version(
            path,
            &schemas,
            &mut total_violations,
            &mut total_integrity,
            &mut results,
            &k8s_version,
            &scan_cache_version,
        ) {
            eprintln!("[ERROR] Scan incomplete: {}", error);
            scan_output::report_failure(args, target, &error.to_string());
            return error.exit_code();
        }
        total_files += 1;
    } else if path.is_dir() {
        // Stream files in bounded batches of 1,000 to keep memory footprint <= 128MB on giant 100k+ mono-repos
        let mut file_batch = Vec::with_capacity(1000);
        let scan_result = scan_walk::visit_matching_files(path, &["yaml", "yml"], |file| {
            file_batch.push(file.to_path_buf());
            if file_batch.len() >= 1000 {
                total_files += file_batch.len();
                for fp in file_batch.drain(..) {
                    if let Err(error) = scan_file::process_file_with_precomputed_cache_version(
                        &fp,
                        &schemas,
                        &mut total_violations,
                        &mut total_integrity,
                        &mut results,
                        &k8s_version,
                        &scan_cache_version,
                    ) {
                        return Err(error);
                    }
                }
            }
            Ok(())
        });
        if let Err(error) = scan_result {
            eprintln!("[ERROR] Directory scan incomplete: {}", error);
            scan_output::report_failure(args, target, &error.to_string());
            return error.exit_code();
        }
        if !file_batch.is_empty() {
            total_files += file_batch.len();
            for fp in file_batch.drain(..) {
                if let Err(error) = scan_file::process_file_with_precomputed_cache_version(
                    &fp,
                    &schemas,
                    &mut total_violations,
                    &mut total_integrity,
                    &mut results,
                    &k8s_version,
                    &scan_cache_version,
                ) {
                    eprintln!("[ERROR] Directory scan incomplete: {}", error);
                    scan_output::report_failure(args, target, &error.to_string());
                    return error.exit_code();
                }
            }
        }
    } else {
        eprintln!("[ERROR] Target path '{}' does not exist.", target);
        scan_output::report_failure(
            args,
            target,
            &format!("Target path '{}' does not exist.", target),
        );
        return 2;
    }

    let exit_zero = args.iter().any(|a| a == "--exit-zero");

    // Deterministic Sort Order: file ASC, line ASC, rule_id ASC
    results.sort_by(|a, b| {
        a.file
            .cmp(&b.file)
            .then_with(|| a.line.cmp(&b.line))
            .then_with(|| a.rule_id.cmp(&b.rule_id))
    });

    let elapsed = start_time.elapsed();

    let rendered_report = match format {
        OutputFormat::Json => render_json(
            total_files,
            total_violations,
            total_integrity,
            elapsed.as_millis(),
            &results,
        ),
        OutputFormat::Sarif => render_sarif(&k8s_version, &results),
        OutputFormat::Text => render_text(
            target,
            &k8s_version,
            total_files,
            total_violations,
            total_integrity,
            elapsed.as_secs_f64() * 1000.0,
        ),
    };

    if let Some(ref out_path) = output_file {
        if let Err(e) = fs::write(out_path, &rendered_report) {
            eprintln!("[ERROR] Failed to write output file '{}': {}", out_path, e);
            return EXIT_SYSTEM_ERROR;
        }
        scan_output::status(
            args,
            format_args!("[OK] Scan report written to '{}'.", out_path),
        );
    } else {
        if quiet && matches!(format, OutputFormat::Text) {
            print!("{}", scan_output::render_violations(&results));
        } else {
            print!("{}", rendered_report);
        }
        if !rendered_report.ends_with('\n') {
            println!();
        }
    }

    if args
        .iter()
        .any(|a| a == "--otel" || a == "--export-metrics")
    {
        let mut telemetry = crate::models::NativeTelemetry::default();
        telemetry.scans_completed = total_files;
        telemetry.potential_outages_prevented = total_integrity;
        telemetry.total_risk_mitigated = (total_violations as f64) * 5.0;
        telemetry.total_time_saved_ms = elapsed.as_millis() as u64;
        eprintln!(
            "\n{}",
            crate::otel_exporter::export_otel_metrics(&telemetry)
        );
    }

    crate::cli::scan_telemetry::push_scan_telemetry(args);

    if exit_zero {
        EXIT_SUCCESS
    } else if fail_on.is_triggered_by(&results) {
        EXIT_VIOLATIONS
    } else {
        EXIT_SUCCESS
    }
}

fn scan_watch_extensions(args: &[String]) -> &'static [&'static str] {
    if args.iter().any(|arg| arg == "--helm") {
        &["yaml", "yml", "tpl"]
    } else {
        &["yaml", "yml"]
    }
}

fn selected_k8s_version(args: &[String]) -> String {
    get_flag_value(args, "--k8s-version")
        .or_else(|| get_flag_value(args, "--kube-version"))
        .or_else(|| get_flag_value(args, "-k"))
        .unwrap_or_else(|| "1.30".to_string())
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct ViolationRecord {
    pub file: String,
    pub check_type: String,
    pub rule_id: String,
    pub message: String,
    pub severity: String,
    pub line: usize,
}

pub fn process_file(
    path: &Path,
    schemas: &[NativeSchema],
    total_violations: &mut usize,
    total_integrity: &mut usize,
    results: &mut Vec<ViolationRecord>,
) -> Result<(), String> {
    scan_file::process_file_with_cache_context(
        path,
        schemas,
        total_violations,
        total_integrity,
        results,
        "1.30",
        "",
    )
    .map_err(|error| error.to_string())
}

pub fn process_manifest_string(
    content: &str,
    display_name: &str,
    schemas: &[NativeSchema],
    total_violations: &mut usize,
    total_integrity: &mut usize,
    results: &mut Vec<ViolationRecord>,
) -> Result<(), String> {
    scan_manifest::process_manifest_string(
        content,
        display_name,
        schemas,
        total_violations,
        total_integrity,
        results,
    )
}

#[cfg(test)]
#[path = "scan_cmd_tests.rs"]
mod tests;
