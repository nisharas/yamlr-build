//! Rollback CLI Command Handler for Standalone Rust Binary.
//!
//! Why: Restores manifests to their exact pre-remediation state using the
//! transactional Write-Ahead Log (WAL) remediation journal. Strictly < 500 lines.

use crate::cli::{EXIT_CONFIG_ERROR, EXIT_SUCCESS, EXIT_SYSTEM_ERROR};
use crate::remediation_io::{native_list_remediations, native_rollback_remediation};

/// Executes the standalone `yamlr rollback` command.
pub fn execute_rollback(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("rollback", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let tx_id = matches.get_one::<String>("transaction").cloned();
    let journal_path = matches
        .get_one::<String>("journal")
        .cloned()
        .unwrap_or_default();
    let list_mode = matches.get_flag("list");

    if list_mode || tx_id.is_none() {
        return match native_list_remediations(journal_path) {
            Ok(entries) => {
                if entries.is_empty() {
                    println!("[INFO] No remediation transactions found in journal.");
                    EXIT_SUCCESS
                } else {
                    println!("=== Yamlr Forensic Remediation Journal ===");
                    println!(
                        "{:<36} | {:<20} | {:<12} | {}",
                        "TRANSACTION ID", "TIMESTAMP", "STATUS", "FILE"
                    );
                    println!("{:-<36}-+-{:-<20}-+-{:-<12}-+-{:-<30}", "", "", "", "");
                    for e in entries.iter().rev().take(20) {
                        println!(
                            "{:<36} | {:<20} | {:<12} | {}",
                            e.transaction_id,
                            e.timestamp.chars().take(19).collect::<String>(),
                            e.status,
                            e.file_path
                        );
                    }
                    if tx_id.is_none() && !list_mode {
                        println!(
                            "\nTo rollback a transaction, run: yamlr rollback <TRANSACTION_ID>"
                        );
                    }
                    EXIT_SUCCESS
                }
            }
            Err(e) => {
                eprintln!("[ERROR] Failed to read remediation journal: {}", e);
                EXIT_SYSTEM_ERROR
            }
        };
    }

    let target_tx = tx_id.unwrap();
    println!(
        "[ACTION] Rolling back remediation transaction: {}",
        target_tx
    );

    match native_rollback_remediation(journal_path, target_tx.clone()) {
        Ok(true) => {
            println!(
                "[SUCCESS] Transaction '{}' successfully rolled back. Manifest restored.",
                target_tx
            );
            EXIT_SUCCESS
        }
        Ok(false) => {
            eprintln!(
                "[ERROR] Transaction '{}' not found or could not be reverted.",
                target_tx
            );
            EXIT_CONFIG_ERROR
        }
        Err(e) => {
            eprintln!("[ERROR] Rollback failed: {}", e);
            EXIT_SYSTEM_ERROR
        }
    }
}
