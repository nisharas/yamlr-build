//! Multi-Tier Umbrella Chart Hierarchy Crawler & Healer.
//!
//! Why: Traverses umbrella charts and nested subcharts (`charts/<subchart>/values.yaml`),
//!      applying surgical values healing across all hierarchy tiers.

use super::values::heal_values_yaml;
pub use crate::models::HelmHealResult;
use std::fs;
use std::path::{Path, PathBuf};

/// Recursively scans an umbrella chart directory and heals all discovered values files.
pub fn heal_umbrella_chart(root_chart_path: &str) -> Result<Vec<HelmHealResult>, String> {
    let mut results = Vec::new();
    let root = Path::new(root_chart_path);

    if !root.is_dir() {
        return Err(format!(
            "Helm chart path '{}' is not a readable directory.",
            root.display()
        ));
    }

    let mut values_files = Vec::new();
    collect_values_files_recursive(root, &mut values_files)?;

    values_files.sort();

    for path in values_files {
        let content = fs::read_to_string(&path).map_err(|error| {
            format!(
                "Failed to read Helm values file '{}': {}",
                path.display(),
                error
            )
        })?;
        let (healed_yaml, changes) = heal_values_yaml(&content);
        let had_changes = !changes.is_empty();
        let file_path = path.to_string_lossy().into_owned();

        results.push(HelmHealResult {
            file_path,
            healed_yaml,
            changes,
            had_changes,
        });
    }

    Ok(results)
}

/// Recursively discovers `values.yaml` and `values-*.yaml` / `values-*.yml` files.
fn collect_values_files_recursive(
    chart_dir: &Path,
    files: &mut Vec<PathBuf>,
) -> Result<(), String> {
    let entries = fs::read_dir(chart_dir).map_err(|error| {
        format!(
            "Failed to list Helm chart directory '{}': {}",
            chart_dir.display(),
            error
        )
    })?;
    for entry in entries {
        let entry = entry.map_err(|error| {
            format!(
                "Failed to read an entry in Helm chart directory '{}': {}",
                chart_dir.display(),
                error
            )
        })?;
        let path = entry.path();
        let file_type = entry.file_type().map_err(|error| {
            format!(
                "Failed to inspect Helm chart path '{}': {}",
                path.display(),
                error
            )
        })?;
        if file_type.is_file() {
            if let Some(file_name) = path.file_name().and_then(|n| n.to_str()) {
                let is_values = file_name == "values.yaml"
                    || file_name == "values.yml"
                    || ((file_name.starts_with("values-") || file_name.starts_with("values_"))
                        && (file_name.ends_with(".yaml") || file_name.ends_with(".yml")));

                if is_values {
                    files.push(path);
                }
            }
        } else if file_type.is_dir() {
            let dir_name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
            // Descend into charts/ directory for subcharts
            if dir_name == "charts" {
                let subchart_entries = fs::read_dir(&path).map_err(|error| {
                    format!(
                        "Failed to list Helm subchart directory '{}': {}",
                        path.display(),
                        error
                    )
                })?;
                for sub_entry in subchart_entries {
                    let sub_entry = sub_entry.map_err(|error| {
                        format!(
                            "Failed to read an entry in Helm subchart directory '{}': {}",
                            path.display(),
                            error
                        )
                    })?;
                    let sub_path = sub_entry.path();
                    let sub_type = sub_entry.file_type().map_err(|error| {
                        format!(
                            "Failed to inspect Helm subchart path '{}': {}",
                            sub_path.display(),
                            error
                        )
                    })?;
                    if sub_type.is_dir() {
                        collect_values_files_recursive(&sub_path, files)?;
                    }
                }
            }
        }
    }
    Ok(())
}
