//! Remediation Journal & Crash-Resilient Atomic Rollback Engine.
//!
//! Why: Ensures complete crash resilience, transactional auditability, and
//! instantaneous single-command rollbacks for all automated manifest mutations.

use chrono::Utc;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use uuid::Uuid;

use crate::models::RemediationEntry;
use crate::sharder::{native_apply_shadow, native_reconstruct_yaml, native_shard};

/// Resolves the default journal path when not explicitly specified.
pub fn default_journal_path() -> PathBuf {
    if let Ok(env_path) = std::env::var("YAMLR_JOURNAL_PATH") {
        return PathBuf::from(env_path);
    }
    if Path::new(".yamlr-journal.jsonl").exists() {
        return PathBuf::from(".yamlr-journal.jsonl");
    }
    let mut home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
    home.push(".yamlr");
    let _ = fs::create_dir_all(&home);
    home.push("remediation_journal.jsonl");
    home
}

/// Applies an AST fix atomically to a manifest file, recording a transactional
/// write-ahead log (WAL) entry with before/after snapshots.
pub fn native_apply_fix_atomic(
    file_path: String,
    field_path: String,
    new_value: String,
    target_kind: Option<String>,
    target_name: Option<String>,
) -> Result<bool, String> {
    // 1. Jail-Safe Path Normalization & Symlink Check
    let path = Path::new(&file_path);
    if file_path.contains("..") {
        return Err(
            "Security Violation: Path traversal attempts (..) are strictly forbidden.".to_string(),
        );
    }

    let metadata = fs::symlink_metadata(path).map_err(|e| format!("Metadata Error: {}", e))?;

    if !metadata.is_file() {
        return Err(
            "Security Violation: Targeted path is not a regular file (Symlinks forbidden)."
                .to_string(),
        );
    }

    // 2. Lock-Aware Atomic Acquisition
    let lock_path = format!("{}.lock", file_path);
    let mut lock_retries = 0;
    let mut _lock_file = None;

    while lock_retries < 10 {
        match fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&lock_path)
        {
            Ok(f) => {
                _lock_file = Some(f);
                break;
            }
            Err(_) => {
                lock_retries += 1;
                std::thread::sleep(std::time::Duration::from_millis(50 * lock_retries));
            }
        }
    }

    if _lock_file.is_none() {
        return Err(
            "Concurrency Error: Could not acquire file lock after multiple retries.".to_string(),
        );
    }

    // 3. Read Original Content
    let content = fs::read_to_string(&file_path).map_err(|e| {
        let _ = fs::remove_file(&lock_path);
        format!("Read Error: {}", e)
    })?;

    let all_shards = native_shard(&content);
    let mut updated_shards = all_shards.clone();
    native_apply_shadow(&content, &mut updated_shards);

    let mut fix_applied = false;
    let mut previous_value = None;
    let mut matched_resource_key = String::new();

    // Group shards by document for multi-document filtering
    let mut doc_starts = vec![0];
    for (i, shard) in updated_shards.iter().enumerate() {
        if shard.is_doc_boundary {
            doc_starts.push(i);
        }
    }

    for i in 0..doc_starts.len() {
        let start = doc_starts[i];
        let end = if i + 1 < doc_starts.len() {
            doc_starts[i + 1]
        } else {
            updated_shards.len()
        };

        let doc_shards = &mut updated_shards[start..end];
        if doc_shards.is_empty() {
            continue;
        }

        let identity = crate::identity::extract_native_identity(doc_shards.to_vec());
        if target_kind.is_some() || target_name.is_some() {
            let mut matched = true;
            if let Some(ref tk) = target_kind {
                if let Some(ref id) = identity {
                    if tk != &id.kind {
                        matched = false;
                    }
                } else {
                    matched = false;
                }
            }
            if let Some(ref tn) = target_name {
                if let Some(ref id) = identity {
                    if tn != &id.name {
                        matched = false;
                    }
                } else {
                    matched = false;
                }
            }
            if !matched {
                continue;
            }
        }

        if let Some(id) = identity {
            matched_resource_key = format!("{}/{}", id.kind, id.name);
        }

        if let Some(idx) = crate::sharder::native_find_shard_by_path(doc_shards, &field_path) {
            previous_value = doc_shards[idx].value.clone();
            doc_shards[idx].value = Some(new_value.clone());
            let indent_str = " ".repeat(doc_shards[idx].original_indent);
            let key = &doc_shards[idx].key;

            if doc_shards[idx].is_list_item {
                doc_shards[idx].raw_line = format!("{}- {}: {}", indent_str, key, new_value);
            } else {
                doc_shards[idx].raw_line = format!("{}{}: {}", indent_str, key, new_value);
            }

            if !doc_shards[idx].comment.is_empty() {
                doc_shards[idx].raw_line =
                    format!("{} {}", doc_shards[idx].raw_line, doc_shards[idx].comment);
            }
            fix_applied = true;
        }
    }

    if fix_applied {
        let new_yaml = native_reconstruct_yaml(&updated_shards);

        // Pre-Write AST Verification
        let verification_shards = native_shard(&new_yaml);
        if verification_shards.is_empty() && !updated_shards.is_empty() {
            let _ = fs::remove_file(&lock_path);
            return Err("Trust Pillar Violation: Mutated YAML failed pre-write AST verification. Original file preserved.".to_string());
        }
        let verification_manifest = crate::structurer::native_structurize(verification_shards);
        if verification_manifest.root.children.is_empty() && !updated_shards.is_empty() {
            let _ = fs::remove_file(&lock_path);
            return Err("Trust Pillar Violation: Mutated YAML produced empty AST tree. Original file preserved.".to_string());
        }

        let tmp_path = format!("{}.yamlr.tmp", file_path);

        // Write to temporary file
        let mut options = fs::OpenOptions::new();
        options.create(true).write(true).truncate(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        let write_result = options.open(&tmp_path).and_then(|mut file| {
            file.write_all(new_yaml.as_bytes())?;
            file.sync_all()
        });
        if let Err(error) = write_result {
            let _ = fs::remove_file(&tmp_path);
            let _ = fs::remove_file(&lock_path);
            return Err(format!("Temporary Manifest Write Error: {}", error));
        }

        // Atomic Rename Loop
        let mut retries = 0;
        loop {
            match fs::rename(&tmp_path, &file_path) {
                Ok(_) => break,
                Err(_) if retries < 5 => {
                    retries += 1;
                    std::thread::sleep(std::time::Duration::from_millis(10 * retries));
                }
                Err(e) => {
                    let _ = fs::remove_file(&lock_path);
                    return Err(format!("Atomic Rename Error: {}", e));
                }
            }
        }

        // 4. Record Transaction Snapshot into Structured Journal
        let tx_id = Uuid::new_v4().to_string();
        let entry = RemediationEntry {
            transaction_id: tx_id,
            timestamp: Utc::now().to_rfc3339(),
            file_path: file_path.clone(),
            resource_key: if matched_resource_key.is_empty() {
                file_path.clone()
            } else {
                matched_resource_key
            },
            field_path,
            previous_value,
            new_value,
            before_snapshot: content,
            after_snapshot: new_yaml,
            status: "COMMITTED".to_string(),
        };

        let jpath = default_journal_path();
        let journal_result = (|| {
            let entry_json = serde_json::to_string(&entry)
                .map_err(|error| format!("Journal Serialization Error: {}", error))?;
            let mut jfile = fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&jpath)
                .map_err(|error| {
                    format!(
                        "Manifest was replaced, but opening the remediation journal '{}' failed: {}",
                        jpath.display(),
                        error
                    )
                })?;
            writeln!(jfile, "{}", entry_json).map_err(|error| {
                format!(
                    "Manifest was replaced, but writing the remediation journal '{}' failed: {}",
                    jpath.display(),
                    error
                )
            })?;
            jfile.sync_all().map_err(|error| {
                format!(
                    "Manifest was replaced, but syncing the remediation journal '{}' failed: {}",
                    jpath.display(),
                    error
                )
            })
        })();

        let _ = fs::remove_file(&lock_path);
        journal_result?;
        return Ok(true);
    }

    let _ = fs::remove_file(&lock_path);
    Ok(false)
}

/// Rolls back a remediation transaction, atomically restoring the exact `before_snapshot`.
pub fn native_rollback_remediation(
    journal_path: String,
    transaction_id: String,
) -> Result<bool, String> {
    let jpath = if journal_path.is_empty() {
        default_journal_path()
    } else {
        PathBuf::from(journal_path)
    };

    if !jpath.exists() {
        return Ok(false);
    }

    let content = fs::read_to_string(&jpath).map_err(|e| format!("Journal Read Error: {}", e))?;

    let mut target_entry: Option<RemediationEntry> = None;
    for (line_number, line) in content.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let entry = serde_json::from_str::<RemediationEntry>(trimmed).map_err(|error| {
            format!(
                "Invalid remediation journal record at line {}: {}",
                line_number + 1,
                error
            )
        })?;
        if entry.transaction_id == transaction_id {
            target_entry = Some(entry);
        }
    }

    let entry = match target_entry {
        Some(e) => e,
        None => return Ok(false),
    };

    // Lock file before restoration
    let lock_path = format!("{}.lock", entry.file_path);
    let _lock = fs::OpenOptions::new()
        .create(true)
        .write(true)
        .open(&lock_path)
        .map_err(|e| format!("Lock Error: {}", e))?;

    let tmp_path = format!("{}.rollback.tmp", entry.file_path);
    fs::write(&tmp_path, &entry.before_snapshot)
        .map_err(|e| format!("Rollback Write Error: {}", e))?;

    fs::rename(&tmp_path, &entry.file_path).map_err(|e| format!("Rollback Rename Error: {}", e))?;

    let _ = fs::remove_file(&lock_path);

    // Append rollback marker to journal
    let rollback_marker = RemediationEntry {
        transaction_id: format!("rb-{}", entry.transaction_id),
        timestamp: Utc::now().to_rfc3339(),
        file_path: entry.file_path,
        resource_key: entry.resource_key,
        field_path: entry.field_path,
        previous_value: Some(entry.new_value),
        new_value: entry.previous_value.unwrap_or_default(),
        before_snapshot: entry.after_snapshot,
        after_snapshot: entry.before_snapshot,
        status: "ROLLED_BACK".to_string(),
    };

    let marker_json = serde_json::to_string(&rollback_marker)
        .map_err(|error| format!("Rollback Journal Serialization Error: {}", error))?;
    let mut jfile = fs::OpenOptions::new()
        .append(true)
        .open(&jpath)
        .map_err(|error| {
            format!(
                "Manifest was rolled back, but opening journal '{}' failed: {}",
                jpath.display(),
                error
            )
        })?;
    writeln!(jfile, "{}", marker_json).map_err(|error| {
        format!(
            "Manifest was rolled back, but writing journal '{}' failed: {}",
            jpath.display(),
            error
        )
    })?;
    jfile.sync_all().map_err(|error| {
        format!(
            "Manifest was rolled back, but syncing journal '{}' failed: {}",
            jpath.display(),
            error
        )
    })?;

    Ok(true)
}

/// Lists all recorded remediation entries from the forensic journal.
pub fn native_list_remediations(journal_path: String) -> Result<Vec<RemediationEntry>, String> {
    let jpath = if journal_path.is_empty() {
        default_journal_path()
    } else {
        PathBuf::from(journal_path)
    };

    if !jpath.exists() {
        return Ok(Vec::new());
    }

    let content = fs::read_to_string(&jpath).map_err(|e| format!("Journal Read Error: {}", e))?;

    let mut entries = Vec::new();
    for (line_number, line) in content.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let entry = serde_json::from_str::<RemediationEntry>(trimmed).map_err(|error| {
            format!(
                "Invalid remediation journal record at line {}: {}",
                line_number + 1,
                error
            )
        })?;
        entries.push(entry);
    }

    Ok(entries)
}

/// Diagnostic journal log line appending with automated secret masking.
pub fn native_log_remediation(
    journal_path: String,
    resource_key: String,
    remediation: String,
) -> Result<(), String> {
    let now = chrono::Local::now();
    let sensitive_keywords = ["password", "token", "secret", "key", "credential", "auth"];
    let mut scrubbed_remediation = remediation.clone();

    let rem_lower = remediation.to_lowercase();
    let is_sensitive = sensitive_keywords.iter().any(|&k| rem_lower.contains(k));
    let is_high_entropy = remediation.len() > 128;

    if is_sensitive || is_high_entropy {
        if let Some(pos) = scrubbed_remediation.find(':') {
            scrubbed_remediation = format!("{}: [MASKED]", &scrubbed_remediation[..pos]);
        } else if let Some(pos) = scrubbed_remediation.find('=') {
            scrubbed_remediation = format!("{} = [MASKED]", &scrubbed_remediation[..pos]);
        } else if is_high_entropy {
            scrubbed_remediation = "[MASKED: HIGH ENTROPY CONTENT]".to_string();
        }
    }

    let log_line = format!(
        "[{}] {}: {}\n",
        now.format("%Y-%m-%d %H:%M:%S"),
        resource_key,
        scrubbed_remediation
    );
    let mut file = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&journal_path)
        .map_err(|e| format!("IO Error: {}", e))?;
    file.write_all(log_line.as_bytes())
        .map_err(|e| format!("IO Error: {}", e))?;
    file.sync_all().map_err(|e| format!("Fsync Error: {}", e))?;
    Ok(())
}
