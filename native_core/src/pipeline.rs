//! Fleet Pipeline Execution & Parallel Scanning Engine.
//!
//! Why: Orchestrates high-throughput parallel manifest scanning, streaming
//! iterators, schema validation, and health scoring across thousands of files.

#[cfg(feature = "python")]
use pyo3::prelude::*;
use rayon::prelude::*;
use std::fs;
use std::sync::mpsc::{channel, Receiver};
use std::thread;

use crate::audit_engine::*;
use crate::discovery::*;
use crate::identity::*;
use crate::models::*;
use crate::native_record_telemetry;
use crate::sharder::*;

#[cfg_attr(feature = "python", pyclass)]
pub struct NativePipelineIterator {
    #[allow(dead_code)]
    receiver: Receiver<ResourceResult>,
}

#[cfg(feature = "python")]
#[pymethods]
impl NativePipelineIterator {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(slf: PyRefMut<'_, Self>) -> Option<ResourceResult> {
        slf.receiver.recv().ok()
    }
}

#[cfg_attr(feature = "python", pyfunction)]
pub fn native_run_pipeline_streaming(
    root_path: String,
    schemas: Vec<NativeSchema>,
) -> NativePipelineIterator {
    let (tx, rx) = channel();

    thread::spawn(move || {
        let discovery = match native_discover_resources(root_path.clone()) {
            Ok(discovery) => discovery,
            Err(error) => {
                let _ = tx.send(discovery_error_result(root_path, error));
                return;
            }
        };
        for res in discovery {
            let content = match fs::read_to_string(&res.file_path) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("[WARN] Failed to read file '{}': {}", res.file_path, e);
                    continue;
                }
            };
            let mut file_violations = Vec::new();

            let shards = native_shard(&content);
            let manifest = crate::structurer::native_structurize(shards);
            let integrity_violations = manifest.integrity_violations;

            if !content.trim().is_empty() {
                for doc_content in content.split("---") {
                    if doc_content.trim().is_empty() {
                        continue;
                    }
                    file_violations.append(&mut native_check_schema_violations(
                        doc_content,
                        schemas.clone(),
                    ));
                }
            }

            let health_score = calculate_health_score(&integrity_violations);

            let result = ResourceResult {
                file_path: res.file_path.clone(),
                identity: res.identity.clone(),
                violations: file_violations,
                integrity_violations,
                health_score,
                suggested_fixes: Vec::new(),
                relationships: Vec::new(),
            };

            if tx.send(result).is_err() {
                break;
            }
        }
    });

    NativePipelineIterator { receiver: rx }
}

#[cfg_attr(feature = "python", pyfunction)]
pub fn native_check_schema_violations(
    doc: &str,
    schemas: Vec<NativeSchema>,
) -> Vec<SchemaViolation> {
    if doc.trim().is_empty() || schemas.is_empty() {
        return Vec::new();
    }

    let shards = native_shard(doc);
    if shards.is_empty() {
        return Vec::new();
    }

    let manifest = crate::structurer::native_structurize(shards);
    crate::schemas::native_validate_ast_against_schema(&manifest, &schemas)
}

#[cfg_attr(feature = "python", pyfunction)]
pub fn native_generate_schema_fixes(doc: &str, schemas: Vec<NativeSchema>) -> Vec<SchemaViolation> {
    let mut violations = native_check_schema_violations(doc, schemas.clone());
    for v in &mut violations {
        let mut prop_type = "string".to_string();
        for schema in &schemas {
            if let Some(prop) = schema.properties.iter().find(|p| p.name == v.field_path) {
                prop_type = prop.prop_type.clone();
                break;
            }
        }
        v.suggested_value = crate::schemas::default_value_for_type(&prop_type);
    }
    violations
}

#[cfg_attr(feature = "python", pyfunction)]
pub fn native_run_pipeline(root_path: String, schemas: Vec<NativeSchema>) -> NativeReport {
    let start_instant = std::time::Instant::now();
    let discovery = match native_discover_resources(root_path.clone()) {
        Ok(discovery) => discovery,
        Err(error) => {
            return NativeReport {
                total_files: 0,
                results: vec![discovery_error_result(root_path, error)],
                total_time_ms: start_instant.elapsed().as_millis() as u64,
                telemetry: NativeTelemetry::new(),
            };
        }
    };
    let total_files = discovery.len();

    let results: Vec<ResourceResult> = discovery
        .par_iter()
        .map(|res| {
            let content = match fs::read_to_string(&res.file_path) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("[WARN] Failed to read file '{}': {}", res.file_path, e);
                    return ResourceResult {
                        file_path: res.file_path.clone(),
                        identity: None,
                        violations: Vec::new(),
                        integrity_violations: vec![IntegrityViolation {
                            check_name: "IO-READ-ERROR".to_string(),
                            severity: "ERROR".to_string(),
                            message: format!(
                                "IO Error: Unable to read file '{}': {}",
                                res.file_path, e
                            ),
                            rule_id: "IO-001".to_string(),
                            line_no: 0,
                        }],
                        health_score: 0.0,
                        suggested_fixes: Vec::new(),
                        relationships: Vec::new(),
                    };
                }
            };
            let mut file_violations = Vec::new();
            let mut file_fixes = Vec::new();

            if !content.trim().is_empty() {
                for doc_content in content.split("---") {
                    let trimmed = doc_content.trim();
                    if trimmed.is_empty() {
                        continue;
                    }
                    file_violations.append(&mut native_check_schema_violations(
                        trimmed,
                        schemas.clone(),
                    ));
                    file_fixes.append(&mut native_generate_schema_fixes(trimmed, schemas.clone()));
                }
            }

            // Single-pass Audit & Scoring with zero redundant clones
            let shards = native_shard(&content);
            let mut integrity_violations = Vec::new();

            // 1. Identity-based Audits (Deprecations) - borrow shards without clone
            if let Some(id) = extract_native_identity_ref(&shards) {
                if let Some(v) = crate::audit_engine::audit_manifest(
                    &id.api_version.unwrap_or_default(),
                    &id.kind,
                ) {
                    integrity_violations.push(v);
                }
            }

            // 2. Shard-level Audits (Images, Resources) - borrow shards without clone
            for shard in &shards {
                if shard.key == "image" && shard.value.is_some() {
                    if let Some(v) = crate::audit_engine::audit_image(shard.value.as_ref().unwrap())
                    {
                        integrity_violations.push(v);
                    }
                }
            }

            // 3. Structural Audits (moves shards directly, zero clones)
            let manifest = crate::structurer::native_structurize(shards);
            integrity_violations.extend(manifest.integrity_violations);

            let health_score = calculate_health_score(&integrity_violations);

            ResourceResult {
                file_path: res.file_path.clone(),
                identity: res.identity.clone(),
                violations: file_violations,
                integrity_violations,
                health_score,
                suggested_fixes: file_fixes,
                relationships: Vec::new(),
            }
        })
        .collect();

    NativeReport {
        total_files,
        results,
        total_time_ms: start_instant.elapsed().as_millis() as u64,
        telemetry: native_record_telemetry(
            NativeTelemetry::new(),
            "SCAN".to_string(),
            total_files as f64 * 0.5,
            0,
            "INFO".to_string(),
        ),
    }
}

fn discovery_error_result(path: String, error: String) -> ResourceResult {
    ResourceResult {
        file_path: path,
        identity: None,
        violations: Vec::new(),
        integrity_violations: vec![IntegrityViolation {
            check_name: "DISCOVERY-ERROR".to_string(),
            severity: "ERROR".to_string(),
            message: error,
            rule_id: "IO-001".to_string(),
            line_no: 0,
        }],
        health_score: 0.0,
        suggested_fixes: Vec::new(),
        relationships: Vec::new(),
    }
}
