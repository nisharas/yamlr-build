//! High-speed manifest healing CLI handler in native Rust.

use clap::{Arg, ArgAction, Command};
use serde::Deserialize;
use std::fs;
use std::path::Path;
use std::time::Instant;
use walkdir::WalkDir;

use crate::cli::{EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_USAGE, EXIT_VIOLATIONS};
use crate::healing::native_reconstruct_from_semantic;
use crate::models::{NativeIdentity, NativeSchema, NativeTelemetry};
use crate::schemas::native_get_schema_for_version;
use crate::sharder::native_shard;
use crate::structurer::native_structurize;

pub fn execute_heal(args: &[String]) -> i32 {
    let start_time = Instant::now();
    let parsed = match parse_heal_arguments(args) {
        Ok(parsed) => parsed,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target = parsed
        .get_one::<String>("target")
        .cloned()
        .unwrap_or_else(|| ".".to_string());
    let k8s_version = parsed
        .get_one::<String>("k8s-version")
        .cloned()
        .unwrap_or_else(|| "1.30".to_string());
    if let Err(error) = crate::schemas::validate_k8s_version(&k8s_version) {
        eprintln!("[ERROR] {}", error);
        return EXIT_USAGE;
    }
    if let Err(error) = crate::schemas::bundler::validate_schema_overrides(&k8s_version) {
        eprintln!("[ERROR] {}", error);
        return EXIT_SYSTEM_ERROR;
    }

    let apply = parsed.get_flag("apply");
    let diff = parsed.get_flag("diff");
    let dry_run = parsed.get_flag("dry-run") || (!apply && !diff);

    let is_helm = parsed.get_flag("helm");
    let is_kustomize = parsed.get_flag("kustomize");

    let format_str = parsed
        .get_one::<String>("output")
        .cloned()
        .unwrap_or_else(|| "text".to_string());
    let format = match crate::cli::OutputFormat::parse(&format_str) {
        Some(format) => format,
        None => {
            eprintln!(
                "[ERROR] Unsupported --output value '{}'. Use text, json, or sarif.",
                format_str
            );
            return EXIT_USAGE;
        }
    };
    if format != crate::cli::OutputFormat::Text {
        eprintln!(
            "[ERROR] The heal command supports text output only; use the webhook for AdmissionReview responses."
        );
        return EXIT_USAGE;
    }

    let schemas = native_get_schema_for_version(&k8s_version);
    let mut total_files = 0;
    let mut total_healed = 0;

    if target == "-" {
        use std::io::Read;
        let mut content = String::new();
        if let Err(error) = std::io::stdin().read_to_string(&mut content) {
            eprintln!("[ERROR] Failed to read YAML from stdin: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
        let (healed, changes) = heal_manifest_string_with_schemas(&content, &schemas);
        if apply || !diff {
            print!("{}", healed);
        } else {
            for change in &changes {
                println!("[PROPOSED FIX] {}", change);
            }
        }
        return EXIT_SUCCESS;
    }

    let path = Path::new(&target);
    let workspace_identities = if path.exists() {
        index_workspace_identities(path)
    } else {
        Vec::new()
    };

    if is_kustomize && path.is_dir() {
        total_files += 1;
        match crate::parsers::kustomize::render_kustomize_directory(path) {
            Ok(rendered) => {
                let (healed, changes) =
                    heal_manifest_string_with_schemas_and_identities(&rendered, &schemas, &workspace_identities);
                if !changes.is_empty() {
                    total_healed += 1;
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
                            return EXIT_SYSTEM_ERROR;
                        }
                        println!(
                            "       [APPLIED] Written composite overlay to '{}'.",
                            out_path.display()
                        );
                    }
                }
            }
            Err(e) => {
                eprintln!("[ERROR] Kustomize rendering failed: {}", e);
                return 2;
            }
        }
    } else if is_helm && path.is_dir() {
        let chart_str = path.to_str().unwrap_or(".");
        let helm_results = match crate::parsers::helm::heal_umbrella_chart(chart_str) {
            Ok(results) => results,
            Err(error) => {
                eprintln!("[ERROR] Helm chart scan incomplete: {}", error);
                return EXIT_SYSTEM_ERROR;
            }
        };
        total_files += helm_results.len();
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
                            return EXIT_SYSTEM_ERROR;
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
                        return EXIT_SYSTEM_ERROR;
                    }
                    println!(
                        "       [APPLIED] Written healed values to '{}'.",
                        hr.file_path
                    );
                }
            }
        }
    } else if path.is_file() {
        total_files += 1;
        match heal_file(path, &schemas, &workspace_identities, dry_run, diff, apply) {
            Ok(true) => total_healed += 1,
            Ok(false) => {}
            Err(error) => {
                eprintln!("[ERROR] Heal incomplete: {}", error);
                return EXIT_SYSTEM_ERROR;
            }
        }
    } else if path.is_dir() {
        for entry in WalkDir::new(path) {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    eprintln!(
                        "[ERROR] Heal incomplete: directory traversal failed: {}",
                        error
                    );
                    return EXIT_SYSTEM_ERROR;
                }
            };
            let p = entry.path();
            if p.is_file() {
                if let Some(ext) = p.extension() {
                    if ext == "yaml" || ext == "yml" {
                        total_files += 1;
                        match heal_file(p, &schemas, &workspace_identities, dry_run, diff, apply) {
                            Ok(true) => total_healed += 1,
                            Ok(false) => {}
                            Err(error) => {
                                eprintln!("[ERROR] Heal incomplete: {}", error);
                                return EXIT_SYSTEM_ERROR;
                            }
                        }
                    }
                }
            }
        }
    } else {
        eprintln!("[ERROR] Target path '{}' does not exist.", target);
        return 2;
    }

    let exit_zero = parsed.get_flag("exit-zero");
    let generate_stubs = parsed.get_flag("generate-stubs");

    if generate_stubs {
        let mut telemetry = NativeTelemetry::new();
        let (stubs, stub_changes) = crate::healers::stub_healer::generate_stubs_for_missing_targets(
            &workspace_identities,
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
                let stubs_file = if Path::new(&target).is_file() {
                    Path::new(&target)
                        .parent()
                        .unwrap_or(Path::new("."))
                        .join("yamlr_generated_stubs.yaml")
                } else {
                    Path::new(&target).join("yamlr_generated_stubs.yaml")
                };
                let combined = stubs.join("\n---\n");
                if let Err(error) = fs::write(&stubs_file, combined) {
                    eprintln!(
                        "[ERROR] Failed to write generated stubs to '{}': {}",
                        stubs_file.display(),
                        error
                    );
                    return EXIT_SYSTEM_ERROR;
                }
                println!("  [OK] Saved stubs to '{}'.", stubs_file.display());
            } else {
                println!("  [DRY-RUN] Pass '--apply' to write stubs to disk.");
            }
        }
    }

    if let Some(opa_file) = parsed.get_one::<String>("ingest-opa") {
        match crate::remediation_io::ingest_and_heal_policy_file(
            Path::new(&opa_file),
            Path::new(&target),
            "opa",
            apply && !dry_run,
        ) {
            Ok(actions) => {
                if !actions.is_empty() {
                    println!(
                        "\n[POLICY INGESTION - OPA] Remediated {} manifest(s):",
                        actions.len()
                    );
                    for a in &actions {
                        println!("  + {}", a);
                    }
                }
            }
            Err(e) => {
                eprintln!("[ERROR] Ingesting OPA report failed: {}", e);
                return 2;
            }
        }
    }

    if let Some(kyverno_file) = parsed.get_one::<String>("ingest-kyverno") {
        match crate::remediation_io::ingest_and_heal_policy_file(
            Path::new(&kyverno_file),
            Path::new(&target),
            "kyverno",
            apply && !dry_run,
        ) {
            Ok(actions) => {
                if !actions.is_empty() {
                    println!(
                        "\n[POLICY INGESTION - KYVERNO] Remediated {} manifest(s):",
                        actions.len()
                    );
                    for a in &actions {
                        println!("  + {}", a);
                    }
                }
            }
            Err(e) => {
                eprintln!("[ERROR] Ingesting Kyverno report failed: {}", e);
                return 2;
            }
        }
    }

    let elapsed = start_time.elapsed();

    println!("\n=== Yamlr Healing Report ===");
    println!("Manifests Audited: {}", total_files);
    println!("Manifests Healed:  {}", total_healed);
    println!(
        "Execution Duration: {:.2}ms",
        elapsed.as_secs_f64() * 1000.0
    );

    if dry_run && total_healed > 0 {
        println!(
            "\n[DRY-RUN] Previews only. Run 'yamlr heal {} --apply' to write mutations to disk.",
            target
        );
    }

    if parsed.get_flag("otel") {
        let mut telemetry = crate::models::NativeTelemetry::default();
        telemetry.scans_completed = total_files;
        telemetry.heals_completed = total_healed;
        telemetry.total_risk_mitigated = (total_healed as f64) * 10.0;
        telemetry.total_time_saved_ms = elapsed.as_millis() as u64;
        eprintln!(
            "\n{}",
            crate::otel_exporter::export_otel_metrics(&telemetry)
        );
    }

    if exit_zero {
        EXIT_SUCCESS
    } else if total_healed > 0 && !apply {
        EXIT_VIOLATIONS
    } else {
        EXIT_SUCCESS
    }
}

pub(crate) fn parse_heal_arguments(args: &[String]) -> Result<clap::ArgMatches, clap::Error> {
    let command_name = if args
        .get(1)
        .is_some_and(|arg| arg.eq_ignore_ascii_case("fix"))
    {
        "fix"
    } else {
        "heal"
    };
    let mut command = Command::new(command_name)
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
            Arg::new("output")
                .long("output")
                .short('o')
                .value_name("FORMAT")
                .value_parser(["text", "json", "sarif"])
                .ignore_case(true),
        )
        .arg(Arg::new("ingest-opa").long("ingest-opa").value_name("PATH"))
        .arg(
            Arg::new("ingest-kyverno")
                .long("ingest-kyverno")
                .value_name("PATH"),
        )
        .arg(
            Arg::new("apply")
                .long("apply")
                .short('a')
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("dry-run")
                .long("dry-run")
                .short('d')
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("generate-stubs")
                .long("generate-stubs")
                .visible_alias("create-stubs")
                .action(ArgAction::SetTrue),
        )
        .arg(
            Arg::new("otel")
                .long("otel")
                .visible_alias("export-metrics")
                .action(ArgAction::SetTrue),
        );
    for name in ["diff", "helm", "kustomize", "exit-zero"] {
        command = command.arg(Arg::new(name).long(name).action(ArgAction::SetTrue));
    }
    crate::cli::parse_command_args(
        command.group(clap::ArgGroup::new("source-adapter").args(["helm", "kustomize"])),
        args,
    )
}

pub fn heal_manifest_string(content: &str) -> (String, Vec<String>) {
    heal_manifest_string_with_schemas(content, &[])
}

pub fn heal_manifest_string_for_version(content: &str, k8s_version: &str) -> (String, Vec<String>) {
    let schemas = native_get_schema_for_version(k8s_version);
    heal_manifest_string_with_schemas(content, &schemas)
}

pub fn heal_manifest_string_with_schemas(
    content: &str,
    schemas: &[NativeSchema],
) -> (String, Vec<String>) {
    heal_manifest_string_with_schemas_and_identities(content, schemas, &[])
}

pub fn heal_manifest_string_with_schemas_and_identities(
    content: &str,
    schemas: &[NativeSchema],
    workspace_identities: &[NativeIdentity],
) -> (String, Vec<String>) {
    if content.trim().is_empty() {
        return (content.to_string(), Vec::new());
    }

    // Check for Helm values configuration document
    if crate::parsers::helm::is_helm_values_content(content) {
        return crate::parsers::helm::heal_values_yaml(content);
    }

    // Helm & Go Template Masking (Feature 13 of 15)
    let (clean_content, mask_reg) = if content.contains("{{") && content.contains("}}") {
        crate::healers::template_masker::mask_template_expressions(content)
    } else {
        (
            content.to_string(),
            crate::healers::template_masker::TemplateMaskRegistry::default(),
        )
    };

    // Extract all identities across multi-document stream for cross-resource alignment
    let mut local_identities = Vec::new();
    for raw_doc in clean_content.split("---") {
        if raw_doc.trim().is_empty() {
            continue;
        }
        let doc_shards = native_shard(raw_doc);
        if let Some(id) = crate::identity::extract_native_identity(doc_shards) {
            local_identities.push(id);
        }
    }

    // Merge workspace identities with local stream identities (local definitions take precedence)
    let mut all_identities = Vec::new();
    let mut seen = std::collections::HashSet::new();
    for id in &local_identities {
        let key = (id.kind.clone(), id.namespace.clone(), id.name.clone());
        if !id.kind.is_empty() || !id.name.is_empty() {
            seen.insert(key);
        }
        all_identities.push(id.clone());
    }
    for id in workspace_identities {
        let key = (id.kind.clone(), id.namespace.clone(), id.name.clone());
        if (!id.kind.is_empty() || !id.name.is_empty()) && !seen.insert(key) {
            continue;
        }
        all_identities.push(id.clone());
    }

    let (healed_yaml, changes) = if clean_content.contains("---") {
        let line_ending = if clean_content.contains("\r\n") {
            "\r\n"
        } else {
            "\n"
        };
        let mut total_changes = Vec::new();
        let mut healed_docs = Vec::new();
        let mut any_doc_changed = false;
        let mut transaction_aborted = false;

        for raw_doc in clean_content.split("---") {
            if raw_doc.trim().is_empty() {
                continue;
            }
            if native_shard(raw_doc).is_empty() {
                transaction_aborted = true;
                break;
            }
            let (doc_healed, doc_changes) = heal_single_document(raw_doc, &all_identities, schemas);

            if !doc_changes.is_empty() {
                if native_shard(&doc_healed).is_empty() {
                    transaction_aborted = true;
                    break;
                }
                any_doc_changed = true;
                total_changes.extend(doc_changes);
                healed_docs.push(doc_healed);
            } else {
                healed_docs.push(raw_doc.trim().to_string());
            }
        }

        let mut ordered_docs = healed_docs;
        let orig_order: Vec<String> = ordered_docs.clone();
        ordered_docs.sort_by_key(|doc| get_manifest_apply_priority(doc));
        let order_changed = ordered_docs != orig_order;

        if order_changed {
            total_changes.push("[TOPOLOGY-001] Sorted multi-document stream to ensure CRDs and foundational resources precede dependents".to_string());
        }

        if transaction_aborted || (!any_doc_changed && !order_changed) {
            (clean_content.to_string(), Vec::new())
        } else {
            let separator = format!("{line_ending}---{line_ending}");
            let combined = ordered_docs.join(&separator);
            let final_yaml = if combined.ends_with(line_ending) {
                combined
            } else {
                format!("{}{}", combined, line_ending)
            };
            (final_yaml, total_changes)
        }
    } else {
        heal_single_document(&clean_content, &all_identities, schemas)
    };

    // Unmask Helm/Go template expressions
    let final_content = if !mask_reg.placeholders.is_empty() {
        crate::healers::template_masker::unmask_template_expressions(&healed_yaml, &mask_reg)
    } else {
        healed_yaml
    };

    (final_content, changes)
}

fn heal_single_document(
    content: &str,
    identities: &[crate::models::NativeIdentity],
    schemas: &[NativeSchema],
) -> (String, Vec<String>) {
    let shards = native_shard(content);
    if shards.is_empty() {
        return (content.to_string(), Vec::new());
    }

    let mut manifest = native_structurize(shards);
    let mut telemetry = NativeTelemetry::new();
    let changes = crate::healing::native_heal_manifest_with_schemas(
        &mut manifest,
        identities,
        &mut telemetry,
        schemas,
    );

    if changes.is_empty() {
        return (content.to_string(), Vec::new());
    }

    let healed = native_reconstruct_from_semantic(&manifest);
    if healed.trim().is_empty() && !content.trim().is_empty() {
        return (content.to_string(), Vec::new());
    }

    (healed, changes)
}

/// Assigns topological apply priority to Kubernetes resource kinds.
/// Lower numbers MUST be applied before higher numbers in kubectl apply streams.
pub fn get_manifest_apply_priority(content: &str) -> u8 {
    let shards = native_shard(content);
    let kind = crate::identity::extract_native_identity_ref(&shards)
        .map(|id| id.kind)
        .unwrap_or_default();

    match kind.as_str() {
        "Namespace" | "CustomResourceDefinition" | "ServiceAccount" => 1,
        "ClusterRole" | "Role" | "ClusterRoleBinding" | "RoleBinding" => 2,
        "ConfigMap" | "Secret" | "StorageClass" | "PersistentVolumeClaim" => 3,
        "Deployment" | "StatefulSet" | "DaemonSet" | "Job" | "CronJob" | "Pod" => 4,
        "Service" | "Ingress" | "NetworkPolicy" | "Gateway" | "HTTPRoute" => 5,
        _ => 6,
    }
}

/// Pre-indexes resource identities across a workspace or directory to enable cross-file reference resolution.
fn index_workspace_identities(path: &Path) -> Vec<NativeIdentity> {
    let search_path = if path.is_file() {
        path.parent()
            .map(|p| {
                if p.as_os_str().is_empty() {
                    ".".to_string()
                } else {
                    p.to_string_lossy().into_owned()
                }
            })
            .unwrap_or_else(|| ".".to_string())
    } else {
        path.to_string_lossy().into_owned()
    };

    crate::discovery::native_discover_resources(search_path)
        .map(|discovery| discovery.into_iter().filter_map(|d| d.identity).collect())
        .unwrap_or_default()
}

fn heal_file(
    path: &Path,
    schemas: &[NativeSchema],
    workspace_identities: &[NativeIdentity],
    dry_run: bool,
    show_diff: bool,
    apply: bool,
) -> Result<bool, String> {
    let content = fs::read_to_string(path)
        .map_err(|error| format!("failed to read '{}': {}", path.display(), error))?;

    let (healed_content, changes) =
        heal_manifest_string_with_schemas_and_identities(&content, schemas, workspace_identities);
    if changes.is_empty() {
        return Ok(false);
    }

    println!("[HEAL] {}", crate::path_utils::normalize_display_path(path));
    for c in &changes {
        println!("       + {}", c);
    }

    if show_diff {
        print_diff(&content, &healed_content);
    }

    if apply && !dry_run {
        let bak_path = path.with_extension(format!(
            "{}.bak",
            path.extension().and_then(|e| e.to_str()).unwrap_or("yaml")
        ));
        if let Err(error) = fs::copy(path, &bak_path) {
            return Err(format!(
                "failed to create safety backup '{}': {}",
                bak_path.display(),
                error
            ));
        }

        if let Err(e) = fs::write(path, &healed_content) {
            let rollback = fs::copy(&bak_path, path);
            return Err(match rollback {
                Ok(_) => format!(
                    "write failed for '{}': {}; original restored from '{}'",
                    path.display(),
                    e,
                    bak_path.display()
                ),
                Err(rollback_error) => format!(
                    "write failed for '{}': {}; rollback from '{}' also failed: {}",
                    path.display(),
                    e,
                    bak_path.display(),
                    rollback_error
                ),
            });
        }

        // Post-Write Invariant Self-Verification across all documents in stream
        let mut post_verify_ok = true;
        for doc in serde_yaml::Deserializer::from_str(&healed_content) {
            if serde_yaml::Value::deserialize(doc).is_err() {
                post_verify_ok = false;
                break;
            }
        }
        if post_verify_ok {
            post_verify_ok = !native_shard(&healed_content).is_empty();
        }

        if !post_verify_ok {
            eprintln!(
                "       [ROLLBACK] Post-write invariant violation! Restoring from {}",
                bak_path.display()
            );
            return match fs::copy(&bak_path, path) {
                Ok(_) => Err(format!(
                    "post-write YAML validation failed for '{}'; original restored from '{}'",
                    path.display(),
                    bak_path.display()
                )),
                Err(error) => Err(format!(
                    "post-write YAML validation failed for '{}'; rollback from '{}' also failed: {}",
                    path.display(),
                    bak_path.display(),
                    error
                )),
            };
        }

        fs::remove_file(&bak_path).map_err(|error| {
            format!(
                "healed '{}' successfully but could not remove backup '{}': {}",
                path.display(),
                bak_path.display(),
                error
            )
        })?;
        println!("       [APPLIED] Written to disk with invariant self-verification.");
    }

    Ok(true)
}

fn print_diff(original: &str, healed: &str) {
    crate::cli::diff_viewer::render_inline_diff(original, healed);
}

#[cfg(test)]
#[path = "heal_cmd_tests.rs"]
mod tests;
