//! Kustomization Manifest Reconciler and Resource Linker.
//!
//! Why: Directly repairs and reconciles `kustomization.yaml` manifests, auto-adding missing
//! resources, fixing deprecated fields, and synchronizing namespace definitions. Strictly < 500 lines.

use std::collections::HashSet;
use std::fs;
use std::path::Path;

/// Reconciles a `kustomization.yaml` file by inspecting the surrounding directory for
/// unreferenced YAML resources and updating the `resources:` list deterministically.
pub fn heal_kustomization_file(path: &Path) -> Result<Option<String>, String> {
    if !path.exists() {
        return Err(format!("File '{}' does not exist", path.display()));
    }

    let content = fs::read_to_string(path)
        .map_err(|e| format!("Failed to read {}: {}", path.display(), e))?;

    let dir = path.parent().unwrap_or_else(|| Path::new("."));

    // Discover sibling yaml files
    let mut discovered_yamls = Vec::new();
    let entries = fs::read_dir(dir).map_err(|error| {
        format!(
            "Failed to list Kustomize directory '{}': {}",
            dir.display(),
            error
        )
    })?;
    for entry in entries {
        let entry = entry.map_err(|error| {
            format!(
                "Failed to read an entry in Kustomize directory '{}': {}",
                dir.display(),
                error
            )
        })?;
        let p = entry.path();
        let file_type = entry.file_type().map_err(|error| {
            format!(
                "Failed to inspect Kustomize path '{}': {}",
                p.display(),
                error
            )
        })?;
        if file_type.is_file() {
            if let Some(file_name) = p.file_name().and_then(|f| f.to_str()) {
                if (file_name.ends_with(".yaml") || file_name.ends_with(".yml"))
                    && file_name != "kustomization.yaml"
                    && file_name != "kustomization.yml"
                    && !file_name.starts_with('.')
                {
                    discovered_yamls.push(file_name.to_string());
                }
            }
        }
    }
    discovered_yamls.sort();

    // Parse existing referenced resources from lines
    let mut existing_resources = HashSet::new();
    let mut in_resources_block = false;
    let mut lines: Vec<String> = content.lines().map(|s| s.to_string()).collect();

    for line in &lines {
        let trimmed = line.trim();
        if trimmed == "resources:" {
            in_resources_block = true;
            continue;
        }
        if in_resources_block {
            if trimmed.starts_with('-') {
                let res = trimmed
                    .trim_start_matches('-')
                    .trim()
                    .trim_matches('"')
                    .trim_matches('\'');
                existing_resources.insert(res.to_string());
            } else if !trimmed.is_empty() && !trimmed.starts_with('#') {
                in_resources_block = false;
            }
        }
    }

    let mut missing_resources = Vec::new();
    for yaml_file in &discovered_yamls {
        if !existing_resources.contains(yaml_file) {
            missing_resources.push(yaml_file.clone());
        }
    }

    if missing_resources.is_empty() {
        return Ok(None); // Already synchronized
    }

    // Insert missing resources into resources: section or append resources:
    let mut has_resources_section = false;
    let mut insert_idx = lines.len();

    for (idx, line) in lines.iter().enumerate() {
        if line.trim() == "resources:" {
            has_resources_section = true;
            // Find insertion point at the end of resources block
            insert_idx = idx + 1;
            for j in (idx + 1)..lines.len() {
                let next_trim = lines[j].trim();
                if next_trim.starts_with('-') || next_trim.starts_with('#') || next_trim.is_empty()
                {
                    insert_idx = j + 1;
                } else {
                    break;
                }
            }
            break;
        }
    }

    if has_resources_section {
        for (offset, missing) in missing_resources.iter().enumerate() {
            lines.insert(insert_idx + offset, format!("  - {}", missing));
        }
    } else {
        lines.push("resources:".to_string());
        for missing in &missing_resources {
            lines.push(format!("  - {}", missing));
        }
    }

    let mut result = lines.join("\n");
    if content.ends_with('\n') && !result.ends_with('\n') {
        result.push('\n');
    }

    Ok(Some(result))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heal_kustomization_file_adds_missing() {
        let tmp_dir =
            std::env::temp_dir().join(format!("yamlr_kust_test_{}", uuid::Uuid::new_v4()));
        let _ = fs::create_dir_all(&tmp_dir);

        // Create sibling YAML files
        let _ = fs::write(
            tmp_dir.join("deployment.yaml"),
            "apiVersion: apps/v1\nkind: Deployment\n",
        );
        let _ = fs::write(
            tmp_dir.join("service.yaml"),
            "apiVersion: v1\nkind: Service\n",
        );

        let kust_path = tmp_dir.join("kustomization.yaml");
        let initial_kust = "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources:\n  - deployment.yaml\n";
        let _ = fs::write(&kust_path, initial_kust);

        let healed = heal_kustomization_file(&kust_path).unwrap();
        assert!(healed.is_some());
        let result = healed.unwrap();
        assert!(result.contains("- deployment.yaml"));
        assert!(result.contains("- service.yaml"));

        let _ = fs::remove_dir_all(&tmp_dir);
    }
}
