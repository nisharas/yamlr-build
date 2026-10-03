//! Custom Resource Definition schema loading for native scans.

use crate::cli::get_flag_value;
use crate::models::NativeSchema;
use crate::schemas::{distill_crd_content, native_get_schema_for_version};
use serde::Deserialize;
use serde_yaml::Value;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};

pub(super) fn cache_version(context: &str, schemas: &[NativeSchema]) -> Result<String, String> {
    let schema_bytes = serde_json::to_vec(schemas)
        .map_err(|error| format!("Unable to fingerprint scan schemas: {}", error))?;
    let mut hasher = Sha256::new();
    hasher.update(b"yamlr-native-scan-cache-v4::");
    hasher.update(env!("CARGO_PKG_VERSION").as_bytes());
    hasher.update(b"::crd=");
    hasher.update(context.as_bytes());
    hasher.update(b"::schemas=");
    hasher.update(schema_bytes);
    Ok(hex::encode(hasher.finalize()))
}

pub(super) fn load_scan_schemas(
    args: &[String],
    k8s_version: &str,
) -> Result<(Vec<NativeSchema>, String), String> {
    crate::schemas::bundler::validate_schema_overrides(k8s_version)?;
    let mut schemas = native_get_schema_for_version(k8s_version);
    let crd_flag = args
        .iter()
        .any(|arg| arg == "--crd" || arg.starts_with("--crd="));
    if !crd_flag {
        return Ok((schemas, String::new()));
    }

    let crd_path = get_flag_value(args, "--crd")
        .filter(|path| !path.trim().is_empty() && !path.starts_with('-'))
        .ok_or_else(|| "--crd requires a file or directory path".to_string())?;
    let custom_schemas = load_crd_schemas(Path::new(&crd_path))?;

    for custom in &custom_schemas {
        schemas.retain(|existing| {
            existing.kind != custom.kind || existing.api_version != custom.api_version
        });
        schemas.push(custom.clone());
    }

    let serialized = serde_json::to_vec(&custom_schemas)
        .map_err(|error| format!("Unable to fingerprint custom CRD schemas: {}", error))?;
    let mut hasher = Sha256::new();
    hasher.update(serialized);
    Ok((schemas, hex::encode(hasher.finalize())))
}

fn load_crd_schemas(path: &Path) -> Result<Vec<NativeSchema>, String> {
    let files = if path.is_file() {
        vec![path.to_path_buf()]
    } else if path.is_dir() {
        let mut files = Vec::new();
        collect_crd_files(path, &mut files)?;
        files
    } else {
        return Err(format!(
            "CRD path '{}' is not a readable file or directory",
            path.display()
        ));
    };

    let mut schemas = Vec::new();
    for file in files {
        let content = fs::read_to_string(&file)
            .map_err(|error| format!("Unable to read CRD file '{}': {}", file.display(), error))?;
        validate_yaml_documents(&file, &content)?;
        schemas.extend(distill_crd_content(&content)?);
    }

    if schemas.is_empty() {
        return Err(format!(
            "No valid CustomResourceDefinition schemas found at '{}'",
            path.display()
        ));
    }

    schemas.sort_by(|left, right| {
        left.api_version
            .cmp(&right.api_version)
            .then_with(|| left.kind.cmp(&right.kind))
    });
    for pair in schemas.windows(2) {
        if pair[0].api_version == pair[1].api_version && pair[0].kind == pair[1].kind {
            return Err(format!(
                "Duplicate CRD schema for kind '{}' and apiVersion '{}'",
                pair[0].kind, pair[0].api_version
            ));
        }
    }
    Ok(schemas)
}

fn collect_crd_files(directory: &Path, files: &mut Vec<PathBuf>) -> Result<(), String> {
    let entries = fs::read_dir(directory).map_err(|error| {
        format!(
            "Unable to read CRD directory '{}': {}",
            directory.display(),
            error
        )
    })?;
    let mut entries = entries.collect::<Result<Vec<_>, _>>().map_err(|error| {
        format!(
            "Unable to enumerate CRD directory '{}': {}",
            directory.display(),
            error
        )
    })?;
    entries.sort_by_key(|entry| entry.file_name());

    for entry in entries {
        let path = entry.path();
        let file_type = entry.file_type().map_err(|error| {
            format!("Unable to inspect CRD path '{}': {}", path.display(), error)
        })?;
        if file_type.is_dir() {
            collect_crd_files(&path, files)?;
        } else if file_type.is_file()
            && path
                .extension()
                .and_then(|extension| extension.to_str())
                .map_or(false, |extension| {
                    extension.eq_ignore_ascii_case("yaml") || extension.eq_ignore_ascii_case("yml")
                })
        {
            files.push(path);
        }
    }
    Ok(())
}

fn validate_yaml_documents(path: &Path, content: &str) -> Result<(), String> {
    let mut document_count = 0;
    for (index, document) in serde_yaml::Deserializer::from_str(content).enumerate() {
        Value::deserialize(document).map_err(|error| {
            format!(
                "Invalid YAML in CRD file '{}' document {}: {}",
                path.display(),
                index + 1,
                error
            )
        })?;
        document_count += 1;
    }
    if document_count == 0 {
        return Err(format!(
            "CRD file '{}' contains no YAML documents",
            path.display()
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    const CRD: &str = "apiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\nmetadata:\n  name: widgets.example.test\nspec:\n  group: example.test\n  names:\n    kind: Widget\n  versions:\n    - name: v1\n      schema:\n        openAPIV3Schema:\n          type: object\n          required: [spec]\n          properties:\n            spec:\n              type: object\n";

    #[test]
    fn loads_single_crd_file_and_distills_its_schema() {
        let directory = tempdir().unwrap();
        let file = directory.path().join("widget.yaml");
        fs::write(&file, CRD).unwrap();

        let schemas = load_crd_schemas(&file).unwrap();

        assert_eq!(schemas.len(), 1);
        assert_eq!(schemas[0].kind, "Widget");
        assert_eq!(schemas[0].api_version, "example.test/v1");
        assert!(schemas[0]
            .properties
            .iter()
            .any(|property| property.name == "spec" && property.required));
    }

    #[test]
    fn loads_yaml_files_recursively_in_deterministic_order() {
        let directory = tempdir().unwrap();
        let nested = directory.path().join("nested");
        fs::create_dir(&nested).unwrap();
        fs::write(
            directory.path().join("z.yaml"),
            CRD.replace("Widget", "ZWidget")
                .replace("widgets.example.test", "zwidgets.example.test"),
        )
        .unwrap();
        fs::write(
            nested.join("a.yml"),
            CRD.replace("Widget", "AWidget")
                .replace("widgets.example.test", "awidgets.example.test"),
        )
        .unwrap();
        fs::write(directory.path().join("ignore.txt"), "not yaml").unwrap();

        let schemas = load_crd_schemas(directory.path()).unwrap();

        assert_eq!(
            schemas
                .iter()
                .map(|schema| schema.kind.as_str())
                .collect::<Vec<_>>(),
            vec!["AWidget", "ZWidget"]
        );
    }

    #[test]
    fn rejects_missing_path_empty_directory_and_missing_flag_value() {
        let directory = tempdir().unwrap();

        assert!(load_crd_schemas(&directory.path().join("missing.yaml")).is_err());
        assert!(load_crd_schemas(directory.path())
            .unwrap_err()
            .contains("No valid"));
        assert!(
            load_scan_schemas(&["yamlr".into(), "scan".into(), "--crd".into()], "1.30")
                .unwrap_err()
                .contains("requires")
        );
    }

    #[test]
    fn rejects_malformed_yaml_in_crd_input() {
        let directory = tempdir().unwrap();
        let file = directory.path().join("broken.yaml");
        fs::write(&file, "kind: [not closed\n").unwrap();

        assert!(load_crd_schemas(&file)
            .unwrap_err()
            .contains("Invalid YAML"));
    }

    #[test]
    fn rejects_duplicate_kind_and_api_version_definitions() {
        let directory = tempdir().unwrap();
        let file = directory.path().join("duplicate.yaml");
        fs::write(&file, format!("{}\n---\n{}", CRD, CRD)).unwrap();

        assert!(load_crd_schemas(&file)
            .unwrap_err()
            .contains("Duplicate CRD schema"));
    }

    #[test]
    fn supplied_crd_overrides_same_embedded_kind_and_version() {
        let directory = tempdir().unwrap();
        let file = directory.path().join("service-monitor.yaml");
        let crd = CRD
            .replace(
                "widgets.example.test",
                "servicemonitors.monitoring.coreos.com",
            )
            .replace("example.test", "monitoring.coreos.com")
            .replace("Widget", "ServiceMonitor")
            .replace("required: [spec]", "required: [customMarker]")
            .replace(
                "            spec:\n              type: object",
                "            customMarker:\n              type: string",
            );
        fs::write(&file, crd).unwrap();
        let args = vec![
            "yamlr".into(),
            "scan".into(),
            ".".into(),
            format!("--crd={}", file.display()),
        ];

        let (schemas, _) = load_scan_schemas(&args, "1.30").unwrap();
        let matching: Vec<_> = schemas
            .iter()
            .filter(|schema| {
                schema.kind == "ServiceMonitor" && schema.api_version == "monitoring.coreos.com/v1"
            })
            .collect();

        assert_eq!(matching.len(), 1);
        assert!(matching[0]
            .properties
            .iter()
            .any(|property| property.name == "customMarker" && property.required));
    }

    #[test]
    fn custom_crd_schema_changes_scan_cache_context() {
        let directory = tempdir().unwrap();
        let file = directory.path().join("widget.yaml");
        fs::write(&file, CRD).unwrap();
        let args = vec![
            "yamlr".into(),
            "scan".into(),
            ".".into(),
            "--crd".into(),
            file.display().to_string(),
        ];

        let (schemas, context) = load_scan_schemas(&args, "1.30").unwrap();

        assert!(!context.is_empty());
        assert!(schemas
            .iter()
            .any(|schema| schema.kind == "Widget" && schema.api_version == "example.test/v1"));
        assert_ne!(
            cache_version("", &schemas).unwrap(),
            cache_version(&context, &schemas).unwrap()
        );
    }
}
