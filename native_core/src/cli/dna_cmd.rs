//! Semantic DNA hashing and integrity fingerprinting CLI handler.
//!
//! Why: Generates deterministic semantic fingerprints that remain stable across
//! whitespace and comment reformatting, enabling GitOps engines to detect true semantic
//! state changes and prevent spurious reconciliation loops.

use std::fs;
use std::path::Path;
use walkdir::WalkDir;

use crate::cli::{
    report_argument_error, support_contract, EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_VIOLATIONS,
};
use crate::identity::extract_native_identity;
use crate::sharder::native_shard;
use crate::telemetry::native_calculate_dna_hash;

/// Executes the semantic DNA fingerprinting command.
///
/// Why: Provides an auditable cryptographic and semantic identity matrix for Kubernetes
/// manifests, supporting both terminal inspection and automated CI/CD verification.
pub fn execute_dna(args: &[String]) -> i32 {
    let matches = match support_contract::parse("dna", args) {
        Ok(matches) => matches,
        Err(error) => return report_argument_error(error),
    };
    let target = matches.get_one::<String>("target").unwrap();
    let is_json = matches.get_flag("json");
    let full_hash = matches.get_flag("full");

    let target_path = Path::new(&target);
    if !target_path.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target);
        return EXIT_VIOLATIONS;
    }

    let mut files = Vec::new();
    if target_path.is_file() {
        files.push(target_path.to_path_buf());
    } else {
        for entry in WalkDir::new(target_path) {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    eprintln!("[ERROR] DNA manifest traversal failed: {}", error);
                    return EXIT_SYSTEM_ERROR;
                }
            };
            let p = entry.path();
            if p.is_file() {
                if let Some(ext) = p.extension() {
                    if ext == "yaml" || ext == "yml" {
                        files.push(p.to_path_buf());
                    }
                }
            }
        }
    }

    if files.is_empty() {
        println!("[WARN] No YAML manifests found in '{}'.", target);
        return EXIT_SUCCESS;
    }

    let mut records = Vec::new();

    for fpath in &files {
        let content = match fs::read_to_string(fpath) {
            Ok(content) => content,
            Err(error) => {
                eprintln!(
                    "[ERROR] Failed to read YAML manifest '{}': {}",
                    fpath.display(),
                    error
                );
                return EXIT_SYSTEM_ERROR;
            }
        };
        let dna = native_calculate_dna_hash(&content);
        let shards = native_shard(&content);
        let identity = extract_native_identity(shards);
        let kind = identity
            .as_ref()
            .map(|i| i.kind.clone())
            .unwrap_or_else(|| "Unknown".to_string());
        let name = identity
            .as_ref()
            .map(|i| i.name.clone())
            .unwrap_or_else(|| "Unknown".to_string());
        let ns = identity
            .as_ref()
            .map(|i| i.namespace.clone())
            .unwrap_or_else(|| "default".to_string());

        let rel_path = fpath
            .strip_prefix(target_path)
            .unwrap_or(fpath)
            .to_string_lossy()
            .replace('\\', "/");

        records.push(serde_json::json!({
            "file": rel_path,
            "dna_hash": dna,
            "kind": kind,
            "name": name,
            "namespace": ns,
        }));
    }

    if is_json {
        let output = serde_json::json!({
            "version": "0.1.0",
            "total_manifests": records.len(),
            "manifests": records,
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&output).unwrap_or_default()
        );
        return EXIT_SUCCESS;
    }

    println!("Yamlr Semantic DNA Fingerprints");
    println!("===============================");
    println!(
        "{:<30} {:<18} {:<18} {:<24}",
        "FILE", "KIND", "NAME", "SEMANTIC DNA"
    );
    println!("{:-<30} {:-<18} {:-<18} {:-<24}", "", "", "", "");

    for r in &records {
        let full = r["dna_hash"].as_str().unwrap_or("");
        let display_hash = if full_hash || full.len() <= 16 {
            full
        } else {
            &full[..16]
        };

        println!(
            "{:<30} {:<18} {:<18} {:<24}",
            truncate_str(r["file"].as_str().unwrap_or(""), 28),
            truncate_str(r["kind"].as_str().unwrap_or(""), 16),
            truncate_str(r["name"].as_str().unwrap_or(""), 16),
            display_hash
        );
    }

    println!("\nTotal Fingerprints: {}", records.len());
    EXIT_SUCCESS
}

fn truncate_str(s: &str, max_len: usize) -> String {
    if s.len() > max_len {
        format!("{}...", &s[..max_len.saturating_sub(3)])
    } else {
        s.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_dna_generation_on_sample() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("deploy.yaml");
        let yaml = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-api
  namespace: prod
spec:
  replicas: 3
"#;
        fs::write(&file_path, yaml).unwrap();

        let args = vec![
            "yamlr".to_string(),
            "dna".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--json".to_string(),
        ];
        assert_eq!(execute_dna(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_dna_empty_dir_returns_success() {
        let dir = tempdir().unwrap();
        let args = vec![
            "yamlr".to_string(),
            "dna".to_string(),
            dir.path().to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_dna(&args), EXIT_SUCCESS);
    }
}
