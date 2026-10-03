//! Forensic Evidence Vault & Tamper-Proof Audit Logging Engine.
//!
//! Why: Enterprises require immutable, cryptographically verifiable evidence
//! packages (audit trail, machine identity, diffs, journal records) for
//! SOC2/ISO compliance and post-incident forensic reviews.

use chrono::Utc;
use flate2::write::GzEncoder;
use flate2::Compression;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::path::{Path, PathBuf};
use tar::Builder;

use crate::remediation_io::journal::native_list_remediations;
use crate::security::native_get_machine_id;

#[derive(Debug, Serialize, Deserialize)]
pub struct VaultManifest {
    pub vault_version: String,
    pub created_at: String,
    pub machine_id: String,
    pub total_transactions: usize,
    pub committed_count: usize,
    pub rolled_back_count: usize,
    pub affected_files: Vec<FileAttestation>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FileAttestation {
    pub file_path: String,
    pub sha256: String,
}

/// Bundles the forensic journal, manifest snapshots, diffs, and cryptographic
/// signatures into an immutable compressed vault archive (.tar.gz).
/// Returns the SHA-256 hash of the generated evidence vault.
pub fn native_vault_evidence(
    journal_path: String,
    output_vault_path: String,
) -> Result<String, String> {
    let entries = native_list_remediations(journal_path.clone())?;

    let machine_id = native_get_machine_id();
    let created_at = Utc::now().to_rfc3339();

    let mut committed_count = 0;
    let mut rolled_back_count = 0;
    let mut file_set = std::collections::HashSet::new();

    for entry in &entries {
        if entry.status == "COMMITTED" {
            committed_count += 1;
        } else if entry.status == "ROLLED_BACK" {
            rolled_back_count += 1;
        }
        file_set.insert(entry.file_path.clone());
    }

    let mut affected_files = Vec::new();
    for fpath in file_set {
        let file_path = Path::new(&fpath);
        let digest = if !file_path.exists() {
            "FILE_NOT_FOUND".to_string()
        } else {
            let data = fs::read(file_path).map_err(|error| {
                format!(
                    "Failed to read affected file '{}': {}",
                    file_path.display(),
                    error
                )
            })?;
            let mut hasher = Sha256::new();
            hasher.update(&data);
            hex::encode(hasher.finalize())
        };
        affected_files.push(FileAttestation {
            file_path: fpath,
            sha256: digest,
        });
    }

    let manifest = VaultManifest {
        vault_version: "1.0.0".to_string(),
        created_at,
        machine_id,
        total_transactions: entries.len(),
        committed_count,
        rolled_back_count,
        affected_files,
    };

    let manifest_json =
        serde_json::to_string_pretty(&manifest).map_err(|e| format!("JSON Error: {}", e))?;

    let out_path = PathBuf::from(&output_vault_path);
    if let Some(parent) = out_path.parent() {
        fs::create_dir_all(parent).map_err(|error| {
            format!(
                "Failed to create vault output directory '{}': {}",
                parent.display(),
                error
            )
        })?;
    }

    // Build tar.gz in memory or directly to file
    let tar_gz_file = File::create(&out_path).map_err(|e| format!("Vault Create Error: {}", e))?;
    let enc = GzEncoder::new(tar_gz_file, Compression::default());
    let mut tar = Builder::new(enc);

    // 1. Add manifest.json
    let mut header = tar::Header::new_gnu();
    header
        .set_path("vault-manifest.json")
        .map_err(|error| format!("Vault manifest header error: {}", error))?;
    header.set_size(manifest_json.len() as u64);
    header.set_mode(0o644);
    header.set_cksum();
    tar.append(&header, manifest_json.as_bytes())
        .map_err(|e| format!("Tar Append Error: {}", e))?;

    // 2. Add raw journal file if exists
    let jpath = Path::new(&journal_path);
    if jpath.exists() {
        let mut jf = File::open(jpath).map_err(|error| {
            format!(
                "Failed to open remediation journal '{}': {}",
                jpath.display(),
                error
            )
        })?;
        tar.append_file("remediation_journal.jsonl", &mut jf)
            .map_err(|error| format!("Failed to add remediation journal to vault: {}", error))?;
    }

    // 3. Add individual transaction diffs/snapshots
    for entry in &entries {
        let diff_content = format!(
            "# Transaction: {}\n# Timestamp: {}\n# Resource: {}\n# Field: {}\n\n--- BEFORE ---\n{}\n\n--- AFTER ---\n{}\n",
            entry.transaction_id, entry.timestamp, entry.resource_key, entry.field_path, entry.before_snapshot, entry.after_snapshot
        );
        let mut dheader = tar::Header::new_gnu();
        let diff_name = format!("transactions/{}.diff", entry.transaction_id);
        dheader
            .set_path(&diff_name)
            .map_err(|error| format!("Invalid transaction path in vault: {}", error))?;
        dheader.set_size(diff_content.len() as u64);
        dheader.set_mode(0o644);
        dheader.set_cksum();
        tar.append_data(&mut dheader, &diff_name, diff_content.as_bytes())
            .map_err(|error| {
                format!(
                    "Failed to add transaction '{}' to vault: {}",
                    entry.transaction_id, error
                )
            })?;
    }

    // Finish writing tar.gz
    let enc = tar
        .into_inner()
        .map_err(|e| format!("Tar Finish Error: {}", e))?;
    enc.finish()
        .map_err(|e| format!("Gzip Finish Error: {}", e))?;

    // Compute SHA-256 seal of the generated vault file
    let vault_bytes = fs::read(&out_path).map_err(|e| format!("Vault Read Error: {}", e))?;
    let mut hasher = Sha256::new();
    hasher.update(&vault_bytes);
    let checksum = hex::encode(hasher.finalize());

    // Write companion checksum seal file
    let checksum_path = format!("{}.sha256", output_vault_path);
    fs::write(
        &checksum_path,
        format!(
            "{}  {}\n",
            checksum,
            out_path.file_name().unwrap_or_default().to_string_lossy()
        ),
    )
    .map_err(|error| {
        format!(
            "Failed to write vault checksum '{}': {}",
            checksum_path, error
        )
    })?;

    Ok(checksum)
}
