//! Project onboarding and configuration initialization CLI handler.
//!
//! Why: Enables developers and platform teams to bootstrap `.yamlr.yaml` configuration,
//! auto-detecting Helm charts and Kustomize overlays, and offering pre-commit and CI setup templates.

use std::fs;
use std::path::Path;

use crate::cli::{report_argument_error, support_contract, EXIT_SUCCESS, EXIT_VIOLATIONS};

/// Executes the workspace configuration initializer.
///
/// Why: Provides an interactive or automated onboarding flow establishing
/// best-practice safety thresholds and GitOps wave configurations.
pub fn execute_init(args: &[String]) -> i32 {
    let matches = match support_contract::parse("init", args) {
        Ok(matches) => matches,
        Err(error) => return report_argument_error(error),
    };
    let target = matches.get_one::<String>("target").unwrap();
    let force = matches.get_flag("force");
    let target_dir = Path::new(&target);

    if !target_dir.exists() {
        eprintln!("[ERROR] Target directory '{}' does not exist.", target);
        return EXIT_VIOLATIONS;
    }

    let config_path = target_dir.join(".yamlr.yaml");
    if config_path.exists() && !force {
        eprintln!(
            "[ERROR] Configuration file '{}' already exists. Use --force to overwrite.",
            config_path.display()
        );
        return EXIT_VIOLATIONS;
    }

    // 1. Detect project characteristics
    let has_helm = target_dir.join("Chart.yaml").exists()
        || target_dir.join("charts").exists()
        || target_dir.join("values.yaml").exists();
    let has_kustomize = target_dir.join("kustomization.yaml").exists()
        || target_dir.join("kustomization.yml").exists();

    let project_type = if has_helm && has_kustomize {
        "Hybrid (Helm + Kustomize)"
    } else if has_helm {
        "Helm Chart"
    } else if has_kustomize {
        "Kustomize Overlay"
    } else {
        "Standard Kubernetes Manifests"
    };

    let template = format!(
        r#"# Yamlr Manifest Safety & Autonomous Resolution Configuration
# Schema: https://yamlr.dev/schema/v1.json

version: 1
project_type: "{}"

# Target Kubernetes version for schema validation and API deprecation checks
k8s_version: "1.30"

# CI/CD Gate Threshold: error, warning, note
fail_on: "error"

# Autonomous Healing Policies
healing:
  enabled: true
  preserve_comments: true
  pin_latest_tags: true
  drop_all_capabilities: true
  enforce_read_only_root_fs: true
  gitops_wave_stamping: true

# Schema & CRD Settings
schemas:
  auto_ingest_crds: true
  custom_crds_dir: "./crds"

# Telemetry & Compliance
telemetry:
  enabled: false # Set to true to export anonymous ROI metrics
"#,
        project_type
    );

    if let Err(e) = fs::write(&config_path, template) {
        eprintln!("[ERROR] Failed to write configuration file: {}", e);
        return EXIT_VIOLATIONS;
    }

    println!("Initialized Yamlr configuration successfully!");
    println!("----------------------------------------------");
    println!("Created:      {}", config_path.display());
    println!("Detected:     {}", project_type);
    println!("\nNext Steps:");
    println!("  1. Run 'yamlr scan' to audit your manifests.");
    println!("  2. Run 'yamlr heal --diff' to preview safe auto-remediations.");
    println!("  3. Add pre-commit hook to .pre-commit-config.yaml:");
    println!("     - repo: https://github.com/yamlr-dev/yamlr");
    println!("       hooks: [id: yamlr-scan, id: yamlr-fmt]");

    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_init_creates_config_file() {
        let dir = tempdir().unwrap();
        let args = vec![
            "yamlr".to_string(),
            "init".to_string(),
            dir.path().to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_init(&args), EXIT_SUCCESS);
        assert!(dir.path().join(".yamlr.yaml").exists());
    }

    #[test]
    fn test_init_no_overwrite_without_force() {
        let dir = tempdir().unwrap();
        let config_file = dir.path().join(".yamlr.yaml");
        fs::write(&config_file, "existing").unwrap();

        let args = vec![
            "yamlr".to_string(),
            "init".to_string(),
            dir.path().to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_init(&args), EXIT_VIOLATIONS);

        let args_force = vec![
            "yamlr".to_string(),
            "init".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--force".to_string(),
        ];
        assert_eq!(execute_init(&args_force), EXIT_SUCCESS);
    }
}
