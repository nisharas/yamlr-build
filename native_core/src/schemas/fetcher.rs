//! Dynamic Kubernetes Schema Fetcher & Distiller.
//!
//! Why: Enables Yamlr to autonomously support future Kubernetes versions (v1.38, v1.39+)
//!      without requiring binary re-compilation or new releases.
//!      Fetches official OpenAPI definitions, distills them, and caches them in ~/.yamlr/schemas/
//!      with strict hermetic offline fallback guardrails.

use std::fs;
use std::path::PathBuf;
use std::process::Command;

/// Returns the user global schema cache directory (~/.yamlr/schemas/).
pub fn get_user_schema_cache_dir() -> Result<PathBuf, String> {
    let home = dirs::home_dir().ok_or_else(|| {
        "Cannot determine the home directory for the Kubernetes schema cache.".to_string()
    })?;
    Ok(home.join(".yamlr").join("schemas"))
}

/// Returns the local project schema cache directory (.yamlr/schemas/).
pub fn get_local_schema_cache_dir() -> PathBuf {
    PathBuf::from(".yamlr").join("schemas")
}

/// Normalizes version string (e.g., "v1.38.0", "v1.38", "1.38", "v1.39-beta.1" -> "1.39").
pub fn normalize_k8s_version(version: &str) -> String {
    let clean = version.trim().trim_start_matches('v');
    let parts: Vec<&str> = clean.split('.').collect();
    if parts.len() >= 2 {
        let minor: String = parts[1]
            .chars()
            .take_while(|c| c.is_ascii_digit())
            .collect();
        format!("{}.{}", parts[0], minor)
    } else {
        clean.to_string()
    }
}

/// Fetches and caches an official Kubernetes schema for the specified version.
///
/// Hermetic Offline Guardrail: If `offline` is true, immediately errors with
/// advisory notice to fall back to the highest embedded baseline.
pub fn fetch_k8s_schema(version: &str, offline: bool) -> Result<PathBuf, String> {
    let normalized = validate_k8s_version(version)?;

    if offline {
        return Err(format!(
            "[OFFLINE] Hermetic mode is active. Cannot fetch remote schema for Kubernetes v{}. Falling back to embedded baseline.",
            normalized
        ));
    }

    let cache_dir = get_user_schema_cache_dir()?;
    fs::create_dir_all(&cache_dir).map_err(|error| {
        format!(
            "Failed to create Kubernetes schema cache directory '{}': {}",
            cache_dir.display(),
            error
        )
    })?;
    let target_file = cache_dir.join(format!("k8s_v{}_distilled.json", normalized));

    // Check if already cached
    if target_file.is_file() {
        let cached_content = fs::read_to_string(&target_file).map_err(|error| {
            format!(
                "Failed to read cached Kubernetes schema '{}': {}",
                target_file.display(),
                error
            )
        })?;
        validate_distilled_schema(&cached_content).map_err(|error| {
            format!(
                "Cached Kubernetes schema '{}' is invalid: {}. Remove the file and retry.",
                target_file.display(),
                error
            )
        })?;
        return Ok(target_file);
    }

    // Try downloading from official / authoritative OpenAPI schema mirrors
    let urls = [
        format!("https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v{}.0-standalone-strict/_definitions.json", normalized),
        format!("https://raw.githubusercontent.com/kubernetes/kubernetes/release-{}/api/openapi-spec/swagger.json", normalized),
    ];

    let temp_download = cache_dir.join(format!("temp_download_{}.json", normalized));
    let mut download_success = false;

    for url in &urls {
        // Execute curl with timeout and redirect following
        let status = Command::new("curl")
            .arg("-sSL")
            .arg("--fail")
            .arg("--connect-timeout")
            .arg("10")
            .arg("--max-time")
            .arg("30")
            .arg(url)
            .arg("-o")
            .arg(&temp_download)
            .status();

        if let Ok(exit_status) = status {
            if exit_status.success() {
                if let Ok(metadata) = fs::metadata(&temp_download) {
                    if metadata.len() > 1024 {
                        download_success = true;
                        break;
                    }
                }
            }
        }
    }

    if !download_success {
        let _ = fs::remove_file(&temp_download);
        return Err(format!(
            "Failed to download OpenAPI schema for Kubernetes v{} from official mirrors. Verify internet connection or specify local schema via --schema-dir.",
            normalized
        ));
    }

    // Distill or format downloaded schema into distilled format
    let raw_content = fs::read_to_string(&temp_download)
        .map_err(|e| format!("Failed to read downloaded schema: {}", e))?;

    let distilled_json = match distill_definitions_or_swagger(&raw_content) {
        Ok(json) => json,
        Err(e) => {
            let _ = fs::remove_file(&temp_download);
            return Err(format!("Failed to parse/distill downloaded schema: {}", e));
        }
    };

    if let Err(error) = validate_distilled_schema(&distilled_json) {
        let _ = fs::remove_file(&temp_download);
        return Err(format!(
            "Downloaded Kubernetes schema for v{} produced invalid distilled data: {}",
            normalized, error
        ));
    }

    fs::write(&target_file, distilled_json).map_err(|e| {
        format!(
            "Failed to write distilled schema to {}: {}",
            target_file.display(),
            e
        )
    })?;

    let _ = fs::remove_file(&temp_download);
    Ok(target_file)
}

pub fn validate_k8s_version(version: &str) -> Result<String, String> {
    let clean = version.trim().strip_prefix('v').unwrap_or(version.trim());
    let invalid = || {
        format!(
            "Invalid Kubernetes version '{}'. Use a version such as 1.38, v1.38.0, or v1.39-beta.1.",
            version
        )
    };
    let (major, remainder) = clean.split_once('.').ok_or_else(invalid)?;
    if major.is_empty() || !major.chars().all(|c| c.is_ascii_digit()) {
        return Err(invalid());
    }

    let minor_len = remainder.chars().take_while(|c| c.is_ascii_digit()).count();
    if minor_len == 0 {
        return Err(invalid());
    }
    let minor = &remainder[..minor_len];
    let suffix = &remainder[minor_len..];

    let valid_prerelease = |value: &str| {
        !value.is_empty()
            && value
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '-')
    };
    let valid_suffix = if suffix.is_empty() {
        true
    } else if let Some(pre) = suffix.strip_prefix('-') {
        valid_prerelease(pre)
    } else if let Some(components) = suffix.strip_prefix('.') {
        let (numeric, prerelease) = components
            .split_once('-')
            .map_or((components, None), |(numeric, pre)| (numeric, Some(pre)));
        !numeric.is_empty()
            && numeric.split('.').all(|component| {
                !component.is_empty() && component.chars().all(|c| c.is_ascii_digit())
            })
            && prerelease.map_or(true, valid_prerelease)
    } else {
        false
    };
    if !valid_suffix {
        return Err(invalid());
    }

    Ok(format!("{}.{}", major, minor))
}

pub(crate) fn validate_distilled_schema(content: &str) -> Result<(), String> {
    let value: serde_json::Value =
        serde_json::from_str(content).map_err(|error| format!("invalid JSON: {}", error))?;
    let schemas = value
        .as_object()
        .ok_or_else(|| "expected a JSON object of resource schemas".to_string())?;
    if schemas.is_empty() {
        return Err("schema object is empty".to_string());
    }
    for (kind, schema) in schemas {
        let schema = schema
            .as_object()
            .ok_or_else(|| format!("resource schema '{}' must be a JSON object", kind))?;
        if let Some(api_version) = schema.get("apiVersion") {
            if !api_version
                .as_str()
                .is_some_and(|value| !value.trim().is_empty())
            {
                return Err(format!(
                    "resource schema '{}' has an invalid apiVersion",
                    kind
                ));
            }
        }
        let fields = schema
            .get("fields")
            .and_then(serde_json::Value::as_object)
            .filter(|fields| !fields.is_empty())
            .ok_or_else(|| {
                format!(
                    "resource schema '{}' must contain a non-empty fields object",
                    kind
                )
            })?;
        for (field_name, field) in fields {
            let field = field.as_object().ok_or_else(|| {
                format!(
                    "field '{}' in resource schema '{}' must be a JSON object",
                    field_name, kind
                )
            })?;
            if field
                .get("type")
                .is_some_and(|field_type| !field_type.is_string())
            {
                return Err(format!(
                    "field '{}' in resource schema '{}' has an invalid type",
                    field_name, kind
                ));
            }
        }
    }
    Ok(())
}

/// Distills definitions JSON or Swagger JSON into compact distilled schema format.
fn distill_definitions_or_swagger(content: &str) -> Result<String, String> {
    let root: serde_json::Value =
        serde_json::from_str(content).map_err(|e| format!("Invalid JSON: {}", e))?;

    let definitions = if let Some(defs) = root.get("definitions").and_then(|d| d.as_object()) {
        defs
    } else if let Some(obj) = root.as_object() {
        obj
    } else {
        return Err("No definitions object found in JSON schema".to_string());
    };

    let mut distilled = serde_json::Map::new();

    for (full_key, def_val) in definitions {
        let kind = full_key.rsplit('.').next().unwrap_or(full_key);
        let mut entry = serde_json::Map::new();

        if let Some(props) = def_val.get("properties").and_then(|p| p.as_object()) {
            let mut fields = serde_json::Map::new();
            for (p_name, p_val) in props {
                let mut field_info = serde_json::Map::new();
                if let Some(t) = p_val.get("type").and_then(|t| t.as_str()) {
                    field_info.insert("type".to_string(), serde_json::Value::String(t.to_string()));
                }
                if let Some(desc) = p_val.get("description").and_then(|d| d.as_str()) {
                    field_info.insert(
                        "description".to_string(),
                        serde_json::Value::String(desc.to_string()),
                    );
                }
                fields.insert(p_name.clone(), serde_json::Value::Object(field_info));
            }
            entry.insert("fields".to_string(), serde_json::Value::Object(fields));
        }

        if let Some(gvk) = def_val
            .get("x-kubernetes-group-version-kind")
            .and_then(|g| g.as_array())
            .and_then(|a| a.first())
        {
            if let Some(group) = gvk.get("group").and_then(|g| g.as_str()) {
                if let Some(version) = gvk.get("version").and_then(|v| v.as_str()) {
                    let api_version = if group.is_empty() {
                        version.to_string()
                    } else {
                        format!("{}/{}", group, version)
                    };
                    entry.insert(
                        "apiVersion".to_string(),
                        serde_json::Value::String(api_version),
                    );
                }
            }
        }

        distilled.insert(kind.to_string(), serde_json::Value::Object(entry));
    }

    serde_json::to_string_pretty(&serde_json::Value::Object(distilled))
        .map_err(|e| format!("Serialization failed: {}", e))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_k8s_version() {
        assert_eq!(normalize_k8s_version("v1.38.0"), "1.38");
        assert_eq!(normalize_k8s_version("1.38"), "1.38");
        assert_eq!(normalize_k8s_version("v1.39-beta.1"), "1.39");
    }

    #[test]
    fn test_offline_rejection() {
        let res = fetch_k8s_schema("1.38", true);
        assert!(res.is_err());
        assert!(res.unwrap_err().contains("Hermetic mode is active"));
    }

    #[test]
    fn test_distill_definitions_or_swagger() {
        let fake_json = r#"{
            "definitions": {
                "io.k8s.api.core.v1.Pod": {
                    "properties": {
                        "apiVersion": { "type": "string" },
                        "kind": { "type": "string" },
                        "metadata": { "type": "object" },
                        "spec": { "type": "object" }
                    },
                    "x-kubernetes-group-version-kind": [
                        { "group": "", "version": "v1", "kind": "Pod" }
                    ]
                }
            }
        }"#;

        let res = distill_definitions_or_swagger(fake_json);
        assert!(res.is_ok());
        let distilled = res.unwrap();
        assert!(distilled.contains("\"Pod\""));
        assert!(distilled.contains("\"apiVersion\": \"v1\""));
    }
}
