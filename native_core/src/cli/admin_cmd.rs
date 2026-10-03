//! Administrative management and engine maintenance CLI handler.
//!
//! Why: Operators and CI runners require discrete maintenance commands (`yamlr admin`)
//! to prune WAL journals, invalidate cached CRD schemas, and reset local configuration safely.

use crate::cli::{EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_USAGE};
use std::fs;

/// Executes the admin subcommands (cache-clear, config-reset, journal-prune).
///
/// Why: Prevents disk bloat and stale schema states in long-running CI worker nodes.
pub fn execute_admin(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("admin", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let subcommand = matches.subcommand_name().unwrap().to_string();

    match subcommand.as_str() {
        "cache-clear" => {
            let cache_dir = dirs::cache_dir()
                .unwrap_or_else(std::env::temp_dir)
                .join("yamlr");
            if cache_dir.exists() {
                if let Err(error) = fs::remove_dir_all(&cache_dir) {
                    eprintln!(
                        "[ERROR] Failed to clear schema cache '{}': {}",
                        cache_dir.display(),
                        error
                    );
                    return EXIT_SYSTEM_ERROR;
                }
                println!(
                    "[OK] Cleared schema cache directory: {}",
                    cache_dir.display()
                );
            } else {
                println!("[OK] Schema cache is already empty.");
            }
            EXIT_SUCCESS
        }
        "journal-prune" => {
            let count = match prune_journals() {
                Ok(count) => count,
                Err(error) => {
                    eprintln!("[ERROR] Failed to prune WAL journals: {}", error);
                    return EXIT_SYSTEM_ERROR;
                }
            };
            println!("[OK] Pruned {} stale WAL journal snapshots.", count);
            EXIT_SUCCESS
        }
        "config-reset" => {
            let cfg = std::path::Path::new(".yamlr.yaml");
            if cfg.exists() {
                if let Err(error) = fs::remove_file(cfg) {
                    eprintln!("[ERROR] Failed to remove '{}': {}", cfg.display(), error);
                    return EXIT_SYSTEM_ERROR;
                }
                println!("[OK] Removed local .yamlr.yaml configuration file.");
            } else {
                println!("[OK] No local .yamlr.yaml found in current directory.");
            }
            EXIT_SUCCESS
        }
        _ => {
            println!("Yamlr Administrative Management");
            println!("Usage: yamlr admin <SUBCOMMAND>");
            println!("\nSubcommands:");
            println!("  cache-clear     Invalidate and purge cached external CRD schemas");
            println!("  journal-prune   Prune old atomic WAL rollback journals");
            println!("  config-reset    Reset workspace .yamlr.yaml to defaults");
            EXIT_USAGE
        }
    }
}

fn prune_journals() -> Result<usize, String> {
    let mut pruned = 0;
    let entries = fs::read_dir(".").map_err(|error| error.to_string())?;
    for entry in entries {
        let entry = entry.map_err(|error| error.to_string())?;
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with(".yamlr_journal_") && name.ends_with(".wal") {
            fs::remove_file(entry.path())
                .map_err(|error| format!("'{}': {}", entry.path().display(), error))?;
            pruned += 1;
        }
    }
    Ok(pruned)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_admin_help_usage() {
        let args = vec!["yamlr".to_string(), "admin".to_string()];
        assert_eq!(execute_admin(&args), EXIT_USAGE);
    }

    #[test]
    fn test_admin_cache_clear_success() {
        let args = vec![
            "yamlr".to_string(),
            "admin".to_string(),
            "cache-clear".to_string(),
        ];
        assert_eq!(execute_admin(&args), EXIT_SUCCESS);
    }

    #[test]
    fn test_admin_journal_prune_success() {
        let args = vec![
            "yamlr".to_string(),
            "admin".to_string(),
            "journal-prune".to_string(),
        ];
        assert_eq!(execute_admin(&args), EXIT_SUCCESS);
    }
}
