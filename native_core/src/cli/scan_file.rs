//! Checked file input and cached validation for native scans.

use std::path::Path;

use crate::models::NativeSchema;

use super::scan_input::ScanError;
use super::ViolationRecord;

pub(super) fn process_file_with_cache_context(
    path: &Path,
    schemas: &[NativeSchema],
    total_violations: &mut usize,
    total_integrity: &mut usize,
    results: &mut Vec<ViolationRecord>,
    k8s_version: &str,
    crd_cache_context: &str,
) -> Result<(), ScanError> {
    let content = read_manifest(path)?;
    let cache = crate::cache::ScanCache::default();
    process_file_with_cache(
        &content,
        path,
        schemas,
        total_violations,
        total_integrity,
        results,
        k8s_version,
        crd_cache_context,
        &cache,
    )
}

fn read_manifest(path: &Path) -> Result<String, ScanError> {
    let mut file = std::fs::File::open(path).map_err(|error| {
        ScanError::System(format!(
            "Cannot read manifest '{}': {error}",
            path.display()
        ))
    })?;
    let content = super::scan_input::read_limited(&mut file, "manifest").map_err(|error| {
        let message = format!("Cannot read manifest '{}': {}", path.display(), error);
        match error {
            ScanError::System(_) => ScanError::System(message),
            ScanError::Input(_) => ScanError::Input(message),
        }
    })?;
    Ok(content)
}

/// A scan-level fingerprint avoids serializing all expanded schemas per file.
pub(super) fn process_file_with_precomputed_cache_version(
    path: &Path,
    schemas: &[NativeSchema],
    total_violations: &mut usize,
    total_integrity: &mut usize,
    results: &mut Vec<ViolationRecord>,
    k8s_version: &str,
    cache_version: &str,
) -> Result<(), ScanError> {
    let content = read_manifest(path)?;
    let cache = crate::cache::ScanCache::default();
    process_file_with_cache_version(
        &content,
        path,
        schemas,
        total_violations,
        total_integrity,
        results,
        k8s_version,
        cache_version,
        &cache,
    )
}

fn process_file_with_cache(
    content: &str,
    path: &Path,
    schemas: &[NativeSchema],
    total_violations: &mut usize,
    total_integrity: &mut usize,
    results: &mut Vec<ViolationRecord>,
    k8s_version: &str,
    crd_cache_context: &str,
    cache: &crate::cache::ScanCache,
) -> Result<(), ScanError> {
    let cache_version =
        super::scan_crd::cache_version(crd_cache_context, schemas).map_err(ScanError::Input)?;
    process_file_with_cache_version(
        content,
        path,
        schemas,
        total_violations,
        total_integrity,
        results,
        k8s_version,
        &cache_version,
        cache,
    )
}

fn process_file_with_cache_version(
    content: &str,
    path: &Path,
    schemas: &[NativeSchema],
    total_violations: &mut usize,
    total_integrity: &mut usize,
    results: &mut Vec<ViolationRecord>,
    k8s_version: &str,
    cache_version: &str,
    cache: &crate::cache::ScanCache,
) -> Result<(), ScanError> {
    let file_str = crate::path_utils::normalize_display_path(path);

    let cache_key = crate::cache::ScanCache::compute_key(content, k8s_version, &cache_version);
    if let Some(cached) = cache.get(&cache_key) {
        *total_violations += cached.total_violations;
        *total_integrity += cached.total_integrity;
        for mut violation in cached.violations {
            violation.file = file_str.clone();
            results.push(violation);
        }
        return Ok(());
    }

    let start_idx = results.len();
    let start_violations = *total_violations;
    let start_integrity = *total_integrity;
    super::process_manifest_string(
        content,
        &file_str,
        schemas,
        total_violations,
        total_integrity,
        results,
    )
    .map_err(ScanError::Input)?;
    let new_violations = results[start_idx..].to_vec();
    let _ = cache.put(
        &cache_key,
        &crate::cache::CachedScanResult {
            violations: new_violations.clone(),
            total_violations: total_violations.saturating_sub(start_violations),
            total_integrity: total_integrity.saturating_sub(start_integrity),
        },
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn invalid_utf8_file_is_reported_instead_of_being_skipped() {
        let dir = tempdir().unwrap();
        let manifest = dir.path().join("unreadable.yaml");
        fs::write(&manifest, [0xff, 0xfe]).unwrap();
        let mut violations = 0;
        let mut integrity = 0;
        let mut results = Vec::new();

        let error = process_file_with_cache_context(
            &manifest,
            &[],
            &mut violations,
            &mut integrity,
            &mut results,
            "1.30",
            "",
        )
        .unwrap_err();

        assert!(error.to_string().contains("Cannot read manifest"));
        assert!(error.to_string().contains("unreadable.yaml"));
        assert_eq!(violations, 0);
        assert_eq!(integrity, 0);
        assert!(results.is_empty());
    }

    #[test]
    fn filesystem_open_failure_uses_system_error_without_partial_findings() {
        let dir = tempdir().unwrap();
        let missing_manifest = dir.path().join("missing").join("pod.yaml");
        let mut violations = 0;
        let mut integrity = 0;
        let mut results = Vec::new();

        let error = process_file_with_cache_context(
            &missing_manifest,
            &[],
            &mut violations,
            &mut integrity,
            &mut results,
            "1.30",
            "",
        )
        .unwrap_err();

        assert!(error.to_string().contains("Cannot read manifest"));
        assert_eq!(error.exit_code(), crate::cli::EXIT_SYSTEM_ERROR);
        assert_eq!(violations, 0);
        assert_eq!(integrity, 0);
        assert!(results.is_empty());
    }

    #[test]
    fn successful_file_reads_keep_scan_results_and_counts() {
        let dir = tempdir().unwrap();
        let manifest = dir.path().join("pod.yaml");
        fs::write(
            &manifest,
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: pod\n",
        )
        .unwrap();
        let schemas = crate::schemas::native_get_schema_for_version("1.30");
        let mut violations = 0;
        let mut integrity = 0;
        let mut results = Vec::new();

        assert!(process_file_with_cache_context(
            &manifest,
            &schemas,
            &mut violations,
            &mut integrity,
            &mut results,
            "1.30",
            "",
        )
        .is_ok());
        assert_eq!(violations, results.len());
    }

    #[test]
    fn cache_entries_are_isolated_by_selected_kubernetes_version() {
        use crate::models::SchemaProperty;

        let dir = tempdir().unwrap();
        let manifest = dir.path().join("widget.yaml");
        fs::write(
            &manifest,
            "apiVersion: example.test/v1\nkind: Widget\nmetadata:\n  name: sample\n",
        )
        .unwrap();
        let cache = crate::cache::ScanCache::new(Some(dir.path().join("cache")));
        let newer_schema = vec![NativeSchema {
            kind: "Widget".to_string(),
            api_version: "example.test/v1".to_string(),
            properties: vec![SchemaProperty {
                name: "spec".to_string(),
                prop_type: "object".to_string(),
                required: true,
                description: "Required widget specification".to_string(),
                enum_values: Vec::new(),
            }],
        }];
        let mut violations = 0;
        let mut integrity = 0;
        let mut results = Vec::new();

        process_file_with_cache(
            &fs::read_to_string(&manifest).unwrap(),
            &manifest,
            &[],
            &mut violations,
            &mut integrity,
            &mut results,
            "1.26",
            "",
            &cache,
        )
        .unwrap();
        assert_eq!(violations, 0);

        process_file_with_cache(
            &fs::read_to_string(&manifest).unwrap(),
            &manifest,
            &newer_schema,
            &mut violations,
            &mut integrity,
            &mut results,
            "1.30",
            "",
            &cache,
        )
        .unwrap();
        assert_eq!(violations, 1);
        assert!(results[0].message.contains("Missing required field 'spec'"));
    }

    #[test]
    fn cache_entries_are_isolated_by_effective_schema_content() {
        use crate::models::SchemaProperty;

        let dir = tempdir().unwrap();
        let manifest = dir.path().join("widget.yaml");
        let content = "apiVersion: example.test/v1\nkind: Widget\nmetadata:\n  name: sample\n";
        fs::write(&manifest, content).unwrap();
        let cache = crate::cache::ScanCache::new(Some(dir.path().join("cache")));
        let schemas = vec![NativeSchema {
            kind: "Widget".to_string(),
            api_version: "example.test/v1".to_string(),
            properties: vec![SchemaProperty {
                name: "spec".to_string(),
                prop_type: "object".to_string(),
                required: true,
                description: "Required widget specification".to_string(),
                enum_values: Vec::new(),
            }],
        }];
        let mut violations = 0;
        let mut integrity = 0;
        let mut results = Vec::new();

        process_file_with_cache(
            content,
            &manifest,
            &[],
            &mut violations,
            &mut integrity,
            &mut results,
            "1.30",
            "",
            &cache,
        )
        .unwrap();
        assert_eq!(violations, 0);

        process_file_with_cache(
            content,
            &manifest,
            &schemas,
            &mut violations,
            &mut integrity,
            &mut results,
            "1.30",
            "",
            &cache,
        )
        .unwrap();
        assert_eq!(violations, 1);
        assert!(results[0].message.contains("Missing required field 'spec'"));
    }

    #[test]
    fn cached_scan_preserves_schema_and_integrity_counts() {
        use crate::models::SchemaProperty;

        let dir = tempdir().unwrap();
        let manifest = dir.path().join("duplicate-widget.yaml");
        let content =
            "apiVersion: example.test/v1\nkind: Widget\nmetadata:\n  name: first\n  name: second\n";
        fs::write(&manifest, content).unwrap();
        let cache = crate::cache::ScanCache::new(Some(dir.path().join("cache")));
        let schemas = vec![NativeSchema {
            kind: "Widget".to_string(),
            api_version: "example.test/v1".to_string(),
            properties: vec![SchemaProperty {
                name: "spec".to_string(),
                prop_type: "object".to_string(),
                required: true,
                description: "Required widget specification".to_string(),
                enum_values: Vec::new(),
            }],
        }];
        let mut cold_violations = 0;
        let mut cold_integrity = 0;
        let mut cold_results = Vec::new();
        process_file_with_cache(
            content,
            &manifest,
            &schemas,
            &mut cold_violations,
            &mut cold_integrity,
            &mut cold_results,
            "1.30",
            "",
            &cache,
        )
        .unwrap();
        assert_eq!(cold_violations, 1);
        assert_eq!(cold_integrity, 1);

        let mut warm_violations = 0;
        let mut warm_integrity = 0;
        let mut warm_results = Vec::new();
        process_file_with_cache(
            content,
            &manifest,
            &schemas,
            &mut warm_violations,
            &mut warm_integrity,
            &mut warm_results,
            "1.30",
            "",
            &cache,
        )
        .unwrap();

        assert_eq!(warm_violations, cold_violations);
        assert_eq!(warm_integrity, cold_integrity);
        assert_eq!(warm_results.len(), cold_results.len());
    }
}
