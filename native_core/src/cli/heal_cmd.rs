//! High-speed manifest healing CLI handler in native Rust.

pub(crate) use crate::cli::heal_args::parse_heal_arguments;
pub use crate::cli::heal_topology::{get_manifest_apply_priority, has_critical_topological_inversion};
pub(crate) use crate::cli::heal_topology::index_workspace_identities;
#[allow(unused_imports)]
pub(crate) use crate::cli::heal_writer::{heal_file, print_diff};
pub(crate) use crate::cli::heal_adapters::{
    handle_policy_ingestion, handle_stub_generation, heal_helm_directory, heal_kustomize_directory,
};
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
    let verify_kubectl = parsed.get_flag("verify-kubectl");

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
    let mut telemetry = NativeTelemetry::new();

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
        match heal_kustomize_directory(
            path,
            &schemas,
            &workspace_identities,
            diff,
            apply,
            dry_run,
        ) {
            Ok(true) => total_healed += 1,
            Ok(false) => {}
            Err(code) => return code,
        }
    } else if is_helm && path.is_dir() {
        match heal_helm_directory(path, diff, apply, dry_run) {
            Ok((scanned, healed)) => {
                total_files += scanned;
                total_healed += healed;
            }
            Err(code) => return code,
        }
    } else if path.is_file() {
        total_files += 1;
        match heal_file(path, &schemas, &workspace_identities, dry_run, diff, apply, verify_kubectl, &mut telemetry) {
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
                        match heal_file(p, &schemas, &workspace_identities, dry_run, diff, apply, verify_kubectl, &mut telemetry) {
                            Ok(true) => total_healed += 1,
                            Ok(false) => {}
                            Err(error) => {
                                eprintln!("[WARN] Skipped '{}': {}", p.display(), error);
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
        if let Err(code) = handle_stub_generation(&target, &workspace_identities, apply, dry_run) {
            return code;
        }
    }

    if let Some(opa_file) = parsed.get_one::<String>("ingest-opa") {
        if let Err(code) = handle_policy_ingestion(&opa_file, &target, "opa", apply, dry_run) {
            return code;
        }
    }

    if let Some(kyverno_file) = parsed.get_one::<String>("ingest-kyverno") {
        if let Err(code) = handle_policy_ingestion(&kyverno_file, &target, "kyverno", apply, dry_run) {
            return code;
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

    telemetry.scans_completed = total_files;
    telemetry.heals_completed = total_healed;
    telemetry.total_time_saved_ms = (telemetry.potential_outages_prevented as u64 * 15 * 60 * 1000)
        + (telemetry.heals_completed as u64 * 5 * 60 * 1000);

    if parsed.get_flag("summary") {
        println!("{}", crate::telemetry::native_get_telemetry_dashboard(&telemetry));
    }

    if parsed.get_flag("otel") {
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
    let mut telemetry = NativeTelemetry::new();
    heal_manifest_string_with_schemas_and_identities_and_telemetry(
        content,
        schemas,
        workspace_identities,
        &mut telemetry,
    )
}

pub fn heal_manifest_string_with_schemas_and_identities_and_telemetry(
    content: &str,
    schemas: &[NativeSchema],
    workspace_identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> (String, Vec<String>) {
    if content.trim().is_empty() {
        return (content.to_string(), Vec::new());
    }

    // Block Scalar Body Indentation Normalization (Rule SYN-015 / Trap 69)
    let (clean_content, mut pre_heal_changes) =
        crate::healers::block_scalar_healer::heal_block_scalar_indentation(content);
    for change in &pre_heal_changes {
        crate::telemetry::native_record_healing_impact(telemetry, change);
    }

    // Orphaned Indented Block Realignment (Rule SYN-016 / Trap 71)
    let (clean_content, orphan_changes) =
        crate::healers::orphaned_indent_healer::heal_orphaned_indented_blocks(&clean_content);
    for change in &orphan_changes {
        crate::telemetry::native_record_healing_impact(telemetry, change);
    }
    pre_heal_changes.extend(orphan_changes);

    // Over-indented Sequence Items Normalization (Rule SYN-017 / Trap 72)
    let (clean_content, seq_changes) =
        crate::healers::sequence_indent_healer::heal_overindented_sequence_items(&clean_content);
    for change in &seq_changes {
        crate::telemetry::native_record_healing_impact(telemetry, change);
    }
    pre_heal_changes.extend(seq_changes);

    // Malformed Standalone Anchor Declarations Normalization (Rule SYN-018 / Trap 73)
    let (clean_content, anchor_changes) =
        crate::healers::anchor_declaration_healer::heal_malformed_anchor_declarations(&clean_content);
    for change in &anchor_changes {
        crate::telemetry::native_record_healing_impact(telemetry, change);
    }
    pre_heal_changes.extend(anchor_changes);

    // Empty Flow Map with Indented Children Normalization (Rule SYN-019 / Trap 77)
    let (clean_content, empty_flow_changes) =
        crate::healers::orphaned_indent_healer::heal_empty_flow_with_indented_children(&clean_content);
    for change in &empty_flow_changes {
        crate::telemetry::native_record_healing_impact(telemetry, change);
    }
    pre_heal_changes.extend(empty_flow_changes);

    // Check for Helm values configuration document
    if crate::parsers::helm::is_helm_values_content(&clean_content) {
        let (values_healed, values_changes) = crate::parsers::helm::heal_values_yaml(&clean_content);
        let mut total_changes = pre_heal_changes;
        total_changes.extend(values_changes);
        return (values_healed, total_changes);
    }

    // Helm & Go Template Masking (Feature 13 of 15)
    let (clean_content, mask_reg) = if clean_content.contains("{{") && clean_content.contains("}}") {
        crate::healers::template_masker::mask_template_expressions(&clean_content)
    } else {
        (
            clean_content,
            crate::healers::template_masker::TemplateMaskRegistry::default(),
        )
    };

    // Extract all identities across multi-document stream for cross-resource alignment
    let mut local_identities = Vec::new();
    for raw_doc in crate::parsers::streaming::stream_document_slices(&clean_content) {
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

    let doc_slices: Vec<&str> =
        crate::parsers::streaming::stream_document_slices(&clean_content).collect();

    let (healed_yaml, changes) = if doc_slices.len() > 1 {
        let line_ending = if clean_content.contains("\r\n") {
            "\r\n"
        } else {
            "\n"
        };
        let mut total_changes = Vec::new();
        let mut healed_docs = Vec::new();
        let mut any_doc_changed = false;
        let mut transaction_aborted = false;

        for raw_doc in &doc_slices {
            if raw_doc.trim().is_empty() {
                continue;
            }
            if native_shard(raw_doc).is_empty() {
                transaction_aborted = true;
                break;
            }
            let (doc_healed, doc_changes) =
                heal_single_document(raw_doc, &all_identities, schemas, telemetry);

            if !doc_changes.is_empty() {
                if native_shard(&doc_healed).is_empty() {
                    transaction_aborted = true;
                    break;
                }
                any_doc_changed = true;
                total_changes.extend(doc_changes);
                healed_docs.push(doc_healed.trim().to_string());
            } else {
                healed_docs.push(raw_doc.trim().to_string());
            }
        }

        let (ordered_docs, order_changed) = if has_critical_topological_inversion(&healed_docs) {
            let mut ordered = healed_docs.clone();
            ordered.sort_by_key(|doc| get_manifest_apply_priority(doc));
            let changed = ordered != healed_docs;
            if changed {
                total_changes.push("[TOPOLOGY-001] Sorted multi-document stream to ensure CRDs and foundational resources precede dependents".to_string());
            }
            (ordered, changed)
        } else {
            (healed_docs, false)
        };

        if transaction_aborted || (!any_doc_changed && !order_changed) {
            (clean_content.to_string(), Vec::new())
        } else {
            let has_leading_boundary = clean_content.trim_start().starts_with("---");
            let separator = format!("{line_ending}---{line_ending}");
            let combined = ordered_docs.join(&separator);
            let mut final_yaml = if has_leading_boundary {
                format!("---{line_ending}{combined}")
            } else {
                combined
            };
            if !final_yaml.ends_with(line_ending) {
                final_yaml.push_str(line_ending);
            }
            (final_yaml, total_changes)
        }
    } else {
        heal_single_document(&clean_content, &all_identities, schemas, telemetry)
    };

    // Unmask Helm/Go template expressions
    let final_content = if !mask_reg.placeholders.is_empty() {
        crate::healers::template_masker::unmask_template_expressions(&healed_yaml, &mask_reg)
    } else {
        healed_yaml
    };

    let mut all_changes = pre_heal_changes;
    all_changes.extend(changes);

    (final_content, all_changes)
}

fn heal_single_document(
    content: &str,
    identities: &[crate::models::NativeIdentity],
    schemas: &[NativeSchema],
    telemetry: &mut NativeTelemetry,
) -> (String, Vec<String>) {
    let shards = native_shard(content);
    if shards.is_empty() {
        return (content.to_string(), Vec::new());
    }

    let mut manifest = native_structurize(shards.clone());
    let mut changes = crate::healing::native_heal_manifest_with_schemas(
        &mut manifest,
        identities,
        telemetry,
        schemas,
    );

    let has_syntax_repair = shards.iter().any(|s| {
        if s.raw_line.trim().is_empty() || s.raw_line.starts_with('#') || s.is_doc_boundary || s.is_table_continuation || s.is_block {
            return false;
        }
        let raw_indent = s.raw_line.len() - s.raw_line.trim_start().len();
        // Missing colon on a key-value pair OR healed indentation shift (e.g. metadata:\nname: web)
        (!s.is_list_item && !s.raw_line.contains(':') && (!s.key.is_empty() || s.value.is_some()))
            || (!s.is_table_continuation && s.indent > raw_indent)
    });

    if changes.is_empty() {
        if has_syntax_repair {
            let healed = native_reconstruct_from_semantic(&manifest);
            if !healed.trim().is_empty() && healed != content {
                let msg = "Remediation [SYN-001]: Realigned missing key-value colon delimiters and malformed indentation to canonical Kubernetes YAML.".to_string();
                crate::telemetry::native_record_healing_impact(telemetry, &msg);
                return (healed, vec![msg]);
            }
        }
        return (content.to_string(), Vec::new());
    }

    if has_syntax_repair {
        changes.push("Remediation [SYN-001]: Realigned missing key-value colon delimiters and malformed indentation to canonical Kubernetes YAML.".to_string());
    }

    let healed = native_reconstruct_from_semantic(&manifest);
    if healed.trim().is_empty() && !content.trim().is_empty() {
        return (content.to_string(), Vec::new());
    }

    (healed, changes)
}

#[cfg(test)]
#[path = "heal_cmd_tests.rs"]
mod tests;
