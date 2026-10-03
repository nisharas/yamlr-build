//! Manifest baseline snapshotting and tamper/drift detection CLI handler.
//!
//! Why: Enables GitOps workflows to establish a cryptographic baseline of approved manifests
//! and detect subsequent unauthorized drift, injections, or manual tampering.

use clap::{Arg, ArgAction, Command};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

use crate::cli::{EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_VIOLATIONS};

#[derive(serde::Serialize, serde::Deserialize, Debug, PartialEq, Eq)]
pub struct BaselineSnapshot {
    pub version: String,
    pub created_at: String,
    pub manifests: BTreeMap<String, String>, // relative path -> sha256 hex
}

/// Executes the baseline snapshot creation or drift verification command.
///
/// Why: Guarantees repository integrity by capturing and diffing manifest fingerprints.
pub fn execute_baseline(args: &[String]) -> i32 {
    let (target, baseline_file, is_create, is_check) = match parse_baseline_args(args) {
        Ok(parsed) => parsed,
        Err(error) => return crate::cli::report_argument_error(error),
    };

    let target_path = Path::new(&target);
    if !target_path.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target);
        return EXIT_VIOLATIONS;
    }

    let mut current_hashes = BTreeMap::new();
    let collect_file =
        |file_path: &Path, map: &mut BTreeMap<String, String>| -> Result<(), String> {
            let bytes = fs::read(file_path).map_err(|error| {
                format!(
                    "Failed to read manifest '{}': {}",
                    file_path.display(),
                    error
                )
            })?;
            let mut hasher = Sha256::new();
            hasher.update(&bytes);
            let hash = hex::encode(hasher.finalize());
            let rel = file_path.strip_prefix(target_path).unwrap_or(file_path);
            map.insert(rel.to_string_lossy().replace('\\', "/"), hash);
            Ok(())
        };

    if target_path.is_file() {
        if let Err(error) = collect_file(target_path, &mut current_hashes) {
            eprintln!("[ERROR] Baseline scan incomplete: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
    } else {
        for entry in WalkDir::new(target_path) {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    eprintln!("[ERROR] Baseline traversal failed: {}", error);
                    return EXIT_SYSTEM_ERROR;
                }
            };
            let p = entry.path();
            if p.is_file() {
                if let Some(ext) = p.extension() {
                    if ext == "yaml" || ext == "yml" {
                        if let Err(error) = collect_file(p, &mut current_hashes) {
                            eprintln!("[ERROR] Baseline scan incomplete: {}", error);
                            return EXIT_SYSTEM_ERROR;
                        }
                    }
                }
            }
        }
    }

    if is_create || (!baseline_file.exists() && !is_check) {
        let snapshot = BaselineSnapshot {
            version: "0.1.0".to_string(),
            created_at: chrono_timestamp(),
            manifests: current_hashes,
        };
        let serialized = match serde_json::to_string_pretty(&snapshot) {
            Ok(serialized) => serialized,
            Err(error) => {
                eprintln!("[ERROR] Failed to serialize baseline snapshot: {}", error);
                return EXIT_SYSTEM_ERROR;
            }
        };
        if let Err(e) = fs::write(&baseline_file, serialized) {
            eprintln!("[ERROR] Failed to write baseline file: {}", e);
            return EXIT_SYSTEM_ERROR;
        }
        println!(
            "[OK] Established baseline snapshot in '{}' ({} manifests).",
            baseline_file.display(),
            snapshot.manifests.len()
        );
        EXIT_SUCCESS
    } else {
        if !baseline_file.exists() {
            eprintln!(
                "[ERROR] Baseline file '{}' not found. Run with '--create' first.",
                baseline_file.display()
            );
            return EXIT_VIOLATIONS;
        }

        let content = match fs::read_to_string(&baseline_file) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("[ERROR] Failed to read baseline file: {}", e);
                return EXIT_VIOLATIONS;
            }
        };

        let baseline: BaselineSnapshot = match serde_json::from_str(&content) {
            Ok(b) => b,
            Err(e) => {
                eprintln!("[ERROR] Invalid baseline file format: {}", e);
                return EXIT_VIOLATIONS;
            }
        };

        let mut drifted = 0;
        println!(
            "Yamlr Baseline Verification against '{}'",
            baseline_file.display()
        );
        println!("--------------------------------------------------");

        for (path, expected_hash) in &baseline.manifests {
            match current_hashes.get(path) {
                Some(current_hash) => {
                    if current_hash != expected_hash {
                        println!("[DRIFT] Manifest modified: {}", path);
                        drifted += 1;
                    }
                }
                None => {
                    println!("[DELETED] Manifest missing: {}", path);
                    drifted += 1;
                }
            }
        }

        for path in current_hashes.keys() {
            if !baseline.manifests.contains_key(path) {
                println!("[UNTRACKED] New manifest detected: {}", path);
                drifted += 1;
            }
        }

        if drifted > 0 {
            println!(
                "\n[FAIL] Detected {} drifted or untracked resources.",
                drifted
            );
            EXIT_VIOLATIONS
        } else {
            println!("\n[PASS] Repository matches baseline snapshot with 100% integrity.");
            EXIT_SUCCESS
        }
    }
}

pub(crate) fn parse_baseline_args(
    args: &[String],
) -> Result<(String, PathBuf, bool, bool), clap::Error> {
    let parsed = crate::cli::parse_command_args(
        Command::new("baseline")
            .about("Snapshot or verify manifest hashes; creates a missing baseline unless --check is used")
            .arg(Arg::new("target").default_value("."))
            .arg(Arg::new("file").long("file").default_value(".yamlr-baseline.json")
                .value_parser(clap::builder::NonEmptyStringValueParser::new()))
            .arg(Arg::new("create").long("create").short('c').action(ArgAction::SetTrue)
                .conflicts_with("check"))
            .arg(Arg::new("check").long("check").action(ArgAction::SetTrue)),
        args,
    )?;
    Ok((
        parsed.get_one::<String>("target").unwrap().clone(),
        PathBuf::from(parsed.get_one::<String>("file").unwrap()),
        parsed.get_flag("create"),
        parsed.get_flag("check"),
    ))
}

fn chrono_timestamp() -> String {
    chrono::Utc::now().to_rfc3339()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cli::EXIT_USAGE;
    use tempfile::tempdir;

    #[test]
    fn conflicting_modes_cannot_overwrite_the_baseline() {
        let dir = tempdir().unwrap();
        let snapshot = dir.path().join("baseline.json");
        fs::write(&snapshot, "reviewed baseline").unwrap();
        let args = vec![
            "yamlr".into(),
            "baseline".into(),
            "--create".into(),
            "--check".into(),
            "--file".into(),
            snapshot.to_string_lossy().into_owned(),
        ];
        assert_eq!(execute_baseline(&args), EXIT_USAGE);
        assert_eq!(fs::read_to_string(snapshot).unwrap(), "reviewed baseline");
    }

    #[test]
    fn test_baseline_creation_and_check() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("pod.yaml");
        fs::write(
            &file_path,
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: app\n",
        )
        .unwrap();

        let baseline_path = dir.path().join("baseline.json");

        // 1. Create baseline
        let args_create = vec![
            "yamlr".to_string(),
            "baseline".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--create".to_string(),
            "--file".to_string(),
            baseline_path.to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_baseline(&args_create), EXIT_SUCCESS);
        assert!(baseline_path.exists());

        // 2. Check baseline (unmodified)
        let args_check = vec![
            "yamlr".to_string(),
            "baseline".to_string(),
            dir.path().to_str().unwrap().to_string(),
            "--check".to_string(),
            "--file".to_string(),
            baseline_path.to_str().unwrap().to_string(),
        ];
        assert_eq!(execute_baseline(&args_check), EXIT_SUCCESS);

        // 3. Mutate manifest and check (must detect drift)
        fs::write(
            &file_path,
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: app-drifted\n",
        )
        .unwrap();
        assert_eq!(execute_baseline(&args_check), EXIT_VIOLATIONS);
    }

    #[test]
    fn accepts_options_before_target_and_rejects_unknown_options() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("pod.yaml");
        fs::write(&file_path, "apiVersion: v1\nkind: Pod\n").unwrap();
        let baseline_path = dir.path().join("baseline.json");
        let args = vec![
            "yamlr".to_string(),
            "baseline".to_string(),
            "--create".to_string(),
            format!("--file={}", baseline_path.display()),
            dir.path().to_string_lossy().into_owned(),
        ];

        assert_eq!(execute_baseline(&args), EXIT_SUCCESS);
        assert!(baseline_path.exists());

        let invalid_args = vec![
            "yamlr".to_string(),
            "baseline".to_string(),
            "--unknown".to_string(),
            dir.path().to_string_lossy().into_owned(),
        ];
        assert_eq!(execute_baseline(&invalid_args), EXIT_USAGE);
    }
}
