//! Workspace and engine status CLI handler.
//!
//! Why: In CI environments and developer terminals, `yamlr status` provides a rapid overview
//! of local configuration, target Kubernetes version, journal rollback states, and license tiers.

use std::fs;
use std::path::Path;

use crate::cli::{EXIT_SUCCESS, EXIT_SYSTEM_ERROR};

/// Displays the current workspace configuration and engine status.
///
/// Why: Allows developers and CI workflows to assert the active configuration state.
pub fn execute_status(_args: &[String]) -> i32 {
    println!("Yamlr Autonomous Resolution Engine — Workspace Status");
    println!("=====================================================");

    // 1. Config status
    let cfg = Path::new(".yamlr.yaml");
    if cfg.exists() {
        println!("Configuration:        Active (.yamlr.yaml detected)");
    } else {
        println!("Configuration:        Zero-Config Defaults (no .yamlr.yaml)");
    }

    // 2. K8s Version Target
    println!("Target K8s Version:   v1.30 (Default, forward compatible to v1.37+)");

    // 3. Engine Architecture
    println!("Engine Core:          Native Rust manifest engine");
    println!(
        "Platform:             {} / {}",
        std::env::consts::OS,
        std::env::consts::ARCH
    );

    // 4. WAL Journal State
    let mut wal_count = 0;
    let entries = match fs::read_dir(".") {
        Ok(entries) => entries,
        Err(error) => {
            eprintln!("[ERROR] Failed to inspect workspace journals: {}", error);
            return EXIT_SYSTEM_ERROR;
        }
    };
    for entry in entries {
        let entry = match entry {
            Ok(entry) => entry,
            Err(error) => {
                eprintln!("[ERROR] Failed to inspect a workspace entry: {}", error);
                return EXIT_SYSTEM_ERROR;
            }
        };
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with(".yamlr_journal_") && name.ends_with(".wal") {
            wal_count += 1;
        }
    }
    println!("Rollback Journals:    {} active WAL snapshots", wal_count);

    // 5. Telemetry & Compliance
    println!("Compliance Gate:      Air-gapped zero-outbound default");
    println!("License Tier:         Community Core (Enterprise Ready)");
    println!("Safety:               Atomic file replacement and remediation journals available");

    EXIT_SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_status_output_success() {
        let args = vec!["yamlr".to_string(), "status".to_string()];
        assert_eq!(execute_status(&args), EXIT_SUCCESS);
    }
}
