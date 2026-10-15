//! Specialized source-adapter handlers for Helm charts and Kustomize overlays.

use std::fs;
use std::path::Path;

use crate::cli::heal_writer::print_diff;
use crate::cli::EXIT_SYSTEM_ERROR;
use crate::models::{NativeIdentity, NativeSchema};

pub(crate) fn heal_kustomize_directory(
    path: &Path,
    schemas: &[NativeSchema],
    workspace_identities: &[NativeIdentity],
    diff: bool,
    apply: bool,
    dry_run: bool,
) -> Result<bool, i32> {
    match crate::parsers::kustomize::render_kustomize_directory(path) {
        Ok(rendered) => {
            let (healed, changes) =
                crate::cli::heal_cmd::heal_manifest_string_with_schemas_and_identities(
                    &rendered,
                    schemas,
                    workspace_identities,
                );
            if !changes.is_empty() {
                println!(
                    "[HEAL] Kustomize overlay: {}",
                    crate::path_utils::normalize_display_path(path)
                );
                for c in &changes {
                    println!("       + {}", c);
                }
                if diff {
                    print_diff(&rendered, &healed);
                }
                if apply && !dry_run {
                    let out_path = path.join("kustomize_healed.yaml");
                    if let Err(error) = fs::write(&out_path, &healed) {
                        eprintln!(
                            "[ERROR] Failed to write healed Kustomize output '{}': {}",
                            out_path.display(),
                            error
                        );
                        return Err(EXIT_SYSTEM_ERROR);
                    }
                    println!(
                        "       [APPLIED] Written composite overlay to '{}'.",
                        out_path.display()
                    );
                }
                Ok(true)
            } else {
                Ok(false)
            }
        }
        Err(e) => {
            eprintln!("[ERROR] Kustomize rendering failed: {}", e);
            Err(2)
        }
    }
}

pub(crate) fn heal_helm_directory(
    path: &Path,
    diff: bool,
    apply: bool,
    dry_run: bool,
) -> Result<(usize, usize), i32> {
    let chart_str = path.to_str().unwrap_or(".");
    let helm_results = match crate::parsers::helm::heal_umbrella_chart(chart_str) {
        Ok(results) => results,
        Err(error) => {
            eprintln!("[ERROR] Helm chart scan incomplete: {}", error);
            return Err(EXIT_SYSTEM_ERROR);
        }
    };
    let total_scanned = helm_results.len();
    let mut total_healed = 0;
    for hr in helm_results {
        if hr.had_changes {
            total_healed += 1;
            println!("[HEAL] Helm values: {}", hr.file_path);
            for c in &hr.changes {
                println!("       + {}", c);
            }
            if diff {
                let orig = match fs::read_to_string(&hr.file_path) {
                    Ok(content) => content,
                    Err(error) => {
                        eprintln!(
                            "[ERROR] Failed to read Helm values file '{}': {}",
                            hr.file_path, error
                        );
                        return Err(EXIT_SYSTEM_ERROR);
                    }
                };
                print_diff(&orig, &hr.healed_yaml);
            }
            if apply && !dry_run {
                if let Err(error) = fs::write(&hr.file_path, &hr.healed_yaml) {
                    eprintln!(
                        "[ERROR] Failed to write healed Helm values file '{}': {}",
                        hr.file_path, error
                    );
                    return Err(EXIT_SYSTEM_ERROR);
                }
                println!(
                    "       [APPLIED] Written healed values to '{}'.",
                    hr.file_path
                );
            }
        }
    }
    Ok((total_scanned, total_healed))
}

pub(crate) fn handle_stub_generation(
    target: &str,
    workspace_identities: &[NativeIdentity],
    apply: bool,
    dry_run: bool,
) -> Result<(), i32> {
    let mut telemetry = crate::models::NativeTelemetry::new();
    let (stubs, stub_changes) = crate::healers::stub_healer::generate_stubs_for_missing_targets(
        workspace_identities,
        &mut telemetry,
    );
    if !stubs.is_empty() {
        println!(
            "\n[STUB GENERATION] Generated {} missing resource stubs:",
            stubs.len()
        );
        for c in &stub_changes {
            println!("  + {}", c);
        }
        if apply && !dry_run {
            let stubs_file = if Path::new(target).is_file() {
                Path::new(target)
                    .parent()
                    .unwrap_or(Path::new("."))
                    .join("yamlr_generated_stubs.yaml")
            } else {
                Path::new(target).join("yamlr_generated_stubs.yaml")
            };
            let combined = stubs.join("\n---\n");
            if let Err(error) = fs::write(&stubs_file, combined) {
                eprintln!(
                    "[ERROR] Failed to write generated stubs to '{}': {}",
                    stubs_file.display(),
                    error
                );
                return Err(EXIT_SYSTEM_ERROR);
            }
            println!("  [OK] Saved stubs to '{}'.", stubs_file.display());
        } else {
            println!("  [DRY-RUN] Pass '--apply' to write stubs to disk.");
        }
    }
    Ok(())
}

pub(crate) fn handle_policy_ingestion(
    policy_file: &str,
    target: &str,
    engine: &str,
    apply: bool,
    dry_run: bool,
) -> Result<(), i32> {
    match crate::remediation_io::ingest_and_heal_policy_file(
        Path::new(policy_file),
        Path::new(target),
        engine,
        apply && !dry_run,
    ) {
        Ok(actions) => {
            if !actions.is_empty() {
                println!(
                    "\n[POLICY INGESTION - {}] Remediated {} manifest(s):",
                    engine.to_uppercase(),
                    actions.len()
                );
                for a in &actions {
                    println!("  + {}", a);
                }
            }
            Ok(())
        }
        Err(e) => {
            eprintln!("[ERROR] Ingesting {} report failed: {}", engine.to_uppercase(), e);
            Err(2)
        }
    }
}
