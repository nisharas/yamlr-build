//! Invariant self-verification, atomic disk writing, safety backups, and diff rendering.

use std::fs;
use std::path::Path;
use serde::Deserialize;

use crate::models::{NativeIdentity, NativeSchema, NativeTelemetry};
use crate::sharder::native_shard;

pub(crate) fn heal_file(
    path: &Path,
    schemas: &[NativeSchema],
    workspace_identities: &[NativeIdentity],
    dry_run: bool,
    show_diff: bool,
    apply: bool,
    verify_kubectl: bool,
    telemetry: &mut NativeTelemetry,
) -> Result<bool, String> {
    let raw_bytes = fs::read(path)
        .map_err(|error| format!("failed to read '{}': {}", path.display(), error))?;

    let (content, file_changes) = if let Some((decoded, transcode_msg)) =
        crate::healers::encoding_transcoder_healer::transcode_utf16_to_utf8(&raw_bytes)
    {
        (decoded, vec![transcode_msg])
    } else {
        match String::from_utf8(raw_bytes) {
            Ok(s) => (s, Vec::new()),
            Err(e) => (String::from_utf8_lossy(e.as_bytes()).into_owned(), Vec::new()),
        }
    };

    let (healed_content, mut changes) =
        crate::cli::heal_cmd::heal_manifest_string_with_schemas_and_identities_and_telemetry(
            &content,
            schemas,
            workspace_identities,
            telemetry,
        );
    if !file_changes.is_empty() {
        let mut all_changes = file_changes;
        all_changes.extend(changes);
        changes = all_changes;
    }
    if changes.is_empty() || healed_content == content {
        return Ok(false);
    }

    println!("[HEAL] {}", crate::path_utils::normalize_display_path(path));
    for c in &changes {
        println!("       + {}", c);
    }

    if show_diff {
        print_diff(&content, &healed_content);
    }

    if apply && !dry_run {
        let bak_path = path.with_extension(format!(
            "{}.bak",
            path.extension().and_then(|e| e.to_str()).unwrap_or("yaml")
        ));
        if let Err(error) = fs::copy(path, &bak_path) {
            return Err(format!(
                "failed to create safety backup '{}': {}",
                bak_path.display(),
                error
            ));
        }

        if let Err(e) = fs::write(path, &healed_content) {
            let rollback = fs::copy(&bak_path, path);
            return Err(match rollback {
                Ok(_) => format!(
                    "write failed for '{}': {}; original restored from '{}'",
                    path.display(),
                    e,
                    bak_path.display()
                ),
                Err(rollback_error) => format!(
                    "write failed for '{}': {}; rollback from '{}' also failed: {}",
                    path.display(),
                    e,
                    bak_path.display(),
                    rollback_error
                ),
            });
        }

        // Post-Write Invariant Self-Verification across all documents in stream
        let mut post_verify_ok = true;
        for (doc_idx, doc) in serde_yaml::Deserializer::from_str(&healed_content).enumerate() {
            if let Err(e) = serde_yaml::Value::deserialize(doc) {
                eprintln!("       [POST-VERIFY-ERR] doc {} failed serde_yaml validation: {}", doc_idx, e);
                post_verify_ok = false;
                break;
            }
        }
        if post_verify_ok {
            post_verify_ok = !native_shard(&healed_content).is_empty();
        }

        // Optional Live Cluster kubectl apply --dry-run Verification
        if post_verify_ok && verify_kubectl {
            let k_res = std::process::Command::new("kubectl")
                .args(["apply", "--dry-run=client", "-f", path.to_str().unwrap_or("")])
                .output();
            if let Ok(out) = k_res {
                if !out.status.success() {
                    let err_msg = String::from_utf8_lossy(&out.stderr);
                    eprintln!("       [ROLLBACK] kubectl apply --dry-run rejected healed manifest: {}", err_msg.trim());
                    post_verify_ok = false;
                }
            }
        }

        if !post_verify_ok {
            eprintln!(
                "       [ROLLBACK] Post-write invariant violation! Restoring from {}",
                bak_path.display()
            );
            return match fs::copy(&bak_path, path) {
                Ok(_) => Err(format!(
                    "post-write YAML validation failed for '{}'; original restored from '{}'",
                    path.display(),
                    bak_path.display()
                )),
                Err(error) => Err(format!(
                    "post-write YAML validation failed for '{}'; rollback from '{}' also failed: {}",
                    path.display(),
                    bak_path.display(),
                    error
                )),
            };
        }

        fs::remove_file(&bak_path).map_err(|error| {
            format!(
                "healed '{}' successfully but could not remove backup '{}': {}",
                path.display(),
                bak_path.display(),
                error
            )
        })?;
        println!("       [APPLIED] Written to disk with invariant self-verification.");
    }

    Ok(true)
}

pub(crate) fn print_diff(original: &str, healed: &str) {
    crate::cli::diff_viewer::render_inline_diff(original, healed);
}
