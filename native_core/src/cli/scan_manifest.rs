//! Per-document validation for native manifest scans.

use crate::models::NativeSchema;
use crate::sharder::{native_shard, native_shard_doc_chunks_from_shards};
use crate::structurer::native_structurize;

use super::ViolationRecord;

const MAX_DOCUMENT_BOUNDARIES: usize = 999;
const MAX_SHARDS: usize = 100_000;

pub(super) fn process_manifest_string(
    content: &str,
    display_name: &str,
    schemas: &[NativeSchema],
    total_violations: &mut usize,
    total_integrity: &mut usize,
    results: &mut Vec<ViolationRecord>,
) -> Result<(), String> {
    if content.len() > super::scan_input::MAX_MANIFEST_BYTES {
        return Err("Manifest exceeds the 10 MiB scan limit; no results were produced".to_string());
    }
    if content.as_bytes().contains(&0) {
        return Err(
            "Manifest contains a NUL byte and cannot be scanned; no results were produced"
                .to_string(),
        );
    }

    let boundary_count = content
        .lines()
        .filter(|line| is_document_boundary(line))
        .count();
    if boundary_count > MAX_DOCUMENT_BOUNDARIES {
        return Err(format!(
            "Manifest exceeds the {} document-boundary scan limit; no results were produced",
            MAX_DOCUMENT_BOUNDARIES
        ));
    }

    let shards = native_shard(content);
    if shards.is_empty() {
        return Ok(());
    }
    if shards
        .last()
        .is_some_and(|last| sharder_truncated_input(content, shards.len(), last.line_no))
    {
        return Err(format!(
            "Manifest exceeds the {}-shard scan limit; no results were produced",
            MAX_SHARDS
        ));
    }

    for document in native_shard_doc_chunks_from_shards(&shards) {
        if document.is_empty() {
            continue;
        }

        let manifest = native_structurize(document);
        let violations = crate::schemas::native_validate_ast_against_schema(&manifest, schemas);
        let integrity = &manifest.integrity_violations;

        *total_violations += violations.len();
        *total_integrity += integrity.len();

        for violation in violations {
            results.push(ViolationRecord {
                file: display_name.to_string(),
                check_type: "schema".to_string(),
                rule_id: "SCH-001".to_string(),
                message: format!("{}: {}", violation.field_path, violation.message),
                severity: violation.severity.to_lowercase(),
                line: violation.line_no.max(1),
            });
        }

        for violation in integrity {
            results.push(ViolationRecord {
                file: display_name.to_string(),
                check_type: "integrity".to_string(),
                rule_id: violation.rule_id.clone(),
                message: violation.message.clone(),
                severity: violation.severity.to_lowercase(),
                line: violation.line_no.max(1),
            });
        }
    }

    // Syntax Self-Healing Audit Pass (Rule SYN-001):
    // Detects when the parser's in-memory lexical physics heuristics had to recover
    // invalid YAML syntax (e.g. missing colons, keyword fusion, unquoted markers).
    // Flags them so the developer knows disk manifests require a write-back fix.
    for shard in &shards {
        if !shard.raw_line.trim().is_empty() && !shard.raw_line.starts_with('#') && !shard.is_doc_boundary {
            let (raw_code, _) = if let Some(idx) = shard.raw_line.find('#') {
                (&shard.raw_line[..idx], &shard.raw_line[idx..])
            } else {
                (shard.raw_line.as_str(), "")
            };
            let trimmed = raw_code.trim();
            // If the raw code was a key-value or mapping without a colon delimiter
            if !trimmed.is_empty()
                && !trimmed.contains(':')
                && !trimmed.starts_with('-')
                && !trimmed.starts_with('{')
                && !trimmed.starts_with('[')
                && (!shard.key.is_empty() || shard.value.is_some())
            {
                *total_integrity += 1;
                results.push(ViolationRecord {
                    file: display_name.to_string(),
                    check_type: "syntax".to_string(),
                    rule_id: "SYN-001".to_string(),
                    message: format!(
                        "Syntax Self-Healing Available: Line {} lacks standard key-value colon delimiter ('{}'). Auto-healed in-memory, run 'yamlr fmt -w' or 'yamlr heal -a' to write back.",
                        shard.line_no,
                        trimmed
                    ),
                    severity: "warning".to_string(),
                    line: shard.line_no.max(1),
                });
            }
        }
    }

    Ok(())
}

fn is_document_boundary(line: &str) -> bool {
    let line = line.trim_end_matches('\r');
    if line.chars().next().is_some_and(char::is_whitespace) {
        return false;
    }
    let comment_index = crate::sharder::native_find_comment_split(line);
    let code = if comment_index >= 0 {
        &line[..comment_index as usize]
    } else {
        line
    };
    let code = code.trim();
    code == "..." || (code.len() >= 3 && code.chars().all(|character| character == '-'))
}

fn sharder_truncated_input(
    content: &str,
    shard_count: usize,
    processed_through_line: usize,
) -> bool {
    shard_count >= MAX_SHARDS
        && content
            .lines()
            .skip(processed_through_line)
            .any(|line| !line.trim().is_empty())
}

#[cfg(test)]
mod tests {
    use super::super::scan_input::MAX_MANIFEST_BYTES;
    use super::*;

    #[test]
    fn multi_document_resources_are_validated_independently() {
        let content = "apiVersion: example.test/v1\nkind: Widget\nmetadata:\n  name: incomplete\n---\napiVersion: example.test/v1\nkind: Widget\nmetadata:\n  name: complete\nspec:\n  enabled: true\n";
        let schemas = [NativeSchema {
            kind: "Widget".to_string(),
            api_version: "example.test/v1".to_string(),
            properties: vec![crate::models::SchemaProperty {
                name: "spec".to_string(),
                prop_type: "object".to_string(),
                required: true,
                description: "Widget specification".to_string(),
                enum_values: Vec::new(),
            }],
        }];
        let mut total_violations = 0;
        let mut total_integrity = 0;
        let mut results = Vec::new();

        process_manifest_string(
            content,
            "widgets.yaml",
            &schemas,
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        )
        .unwrap();

        assert_eq!(total_violations, 1);
        assert_eq!(total_integrity, 0);
        assert_eq!(results.len(), 1);
        assert!(results[0].message.contains("Missing required field 'spec'"));
        assert_eq!(results[0].line, 2);
    }

    #[test]
    fn rejects_documents_beyond_the_sharder_limit_without_partial_results() {
        let content = format!("kind: Widget\n{}", "---\nkind: Widget\n".repeat(1000));
        let mut total_violations = 0;
        let mut total_integrity = 0;
        let mut results = Vec::new();

        let error = process_manifest_string(
            &content,
            "many-documents.yaml",
            &[],
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        )
        .unwrap_err();

        assert!(error.contains("document-boundary scan limit"));
        assert_eq!(total_violations, 0);
        assert_eq!(total_integrity, 0);
        assert!(results.is_empty());
    }

    #[test]
    fn does_not_treat_indented_separator_text_as_a_document_boundary() {
        assert!(!is_document_boundary("  ---"));
        assert!(!is_document_boundary("  ..."));
        assert!(is_document_boundary("--- # next resource"));
        assert!(is_document_boundary("..."));
    }

    #[test]
    fn rejects_oversized_manifest_before_sharder_marker_can_look_clean() {
        let content = "x".repeat(MAX_MANIFEST_BYTES + 1);
        let mut total_violations = 0;
        let mut total_integrity = 0;
        let mut results = Vec::new();

        let error = process_manifest_string(
            &content,
            "oversized.yaml",
            &[],
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        )
        .unwrap_err();

        assert!(error.contains("10 MiB scan limit"));
        assert_eq!(total_violations, 0);
        assert_eq!(total_integrity, 0);
        assert!(results.is_empty());
    }

    #[test]
    fn rejects_nul_containing_manifest_instead_of_treating_empty_shards_as_clean() {
        let content = "apiVersion: v1\nkind: Pod\n\0metadata:\n  name: pod\n";
        let mut total_violations = 0;
        let mut total_integrity = 0;
        let mut results = Vec::new();

        let error = process_manifest_string(
            content,
            "binary.yaml",
            &[],
            &mut total_violations,
            &mut total_integrity,
            &mut results,
        )
        .unwrap_err();

        assert!(error.contains("NUL byte"));
        assert_eq!(total_violations, 0);
        assert_eq!(total_integrity, 0);
        assert!(results.is_empty());
    }

    #[test]
    fn detects_unprocessed_content_only_when_sharder_reaches_its_limit() {
        let content = "processed: value\nunprocessed: value\n";

        assert!(sharder_truncated_input(content, MAX_SHARDS, 1));
        assert!(!sharder_truncated_input(content, MAX_SHARDS - 1, 1));
        assert!(!sharder_truncated_input(content, MAX_SHARDS, 2));
    }
}
