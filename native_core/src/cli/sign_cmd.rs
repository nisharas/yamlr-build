//! Manifest Cryptographic Sign and Verify CLI Command Handler.
//!
//! Why: Enables deterministic GitOps signing and pre-deployment tampering verification
//! directly from the standalone native Rust binary. Strictly < 500 lines.

use std::fs;
use std::path::Path;
use walkdir::WalkDir;

use crate::cli::{EXIT_CONFIG_ERROR, EXIT_SUCCESS, EXIT_SYSTEM_ERROR, EXIT_VIOLATIONS};
use crate::security::signature::{
    extract_manifest_signature, sign_manifest_hmac, verify_manifest_hmac,
};

/// Executes the standalone `yamlr sign` command.
pub fn execute_sign(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("sign", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target_path = matches.get_one::<String>("target").unwrap().clone();
    let key = matches
        .get_one::<String>("key")
        .cloned()
        .or_else(|| std::env::var("YAMLR_SIGN_KEY").ok())
        .filter(|value| !value.trim().is_empty());
    let in_place = matches.get_flag("write");

    let key = match key.filter(|value| !value.trim().is_empty()) {
        Some(key) => key,
        None => {
            eprintln!("[ERROR] Signing requires --key <value> or YAMLR_SIGN_KEY.");
            return EXIT_CONFIG_ERROR;
        }
    };

    let p = Path::new(&target_path);
    if !p.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target_path);
        return EXIT_CONFIG_ERROR;
    }

    if p.is_file() {
        sign_file(p, &key, in_place)
    } else {
        let mut signed_count = 0;
        for entry in WalkDir::new(p).follow_links(false) {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    eprintln!("[ERROR] Signing traversal failed: {}", error);
                    return EXIT_SYSTEM_ERROR;
                }
            };
            let path = entry.path();
            if path.is_file() {
                if let Some(ext) = path.extension() {
                    if ext == "yaml" || ext == "yml" {
                        let result = sign_file(path, &key, in_place);
                        if result != EXIT_SUCCESS {
                            return result;
                        }
                        signed_count += 1;
                    }
                }
            }
        }
        println!(
            "[SUCCESS] Signed {} manifest(s) using HMAC-SHA256.",
            signed_count
        );
        EXIT_SUCCESS
    }
}

fn sign_file(path: &Path, key: &str, in_place: bool) -> i32 {
    match fs::read_to_string(path) {
        Ok(content) => {
            let signed = sign_manifest_hmac(&content, key);
            if in_place {
                if let Err(e) = fs::write(path, signed) {
                    eprintln!(
                        "[ERROR] Failed to write signed file {}: {}",
                        path.display(),
                        e
                    );
                    return EXIT_SYSTEM_ERROR;
                }
                println!("[SIGNED] {}", path.display());
            } else {
                println!("{}", signed);
            }
            EXIT_SUCCESS
        }
        Err(e) => {
            eprintln!("[ERROR] Failed to read {}: {}", path.display(), e);
            EXIT_SYSTEM_ERROR
        }
    }
}

/// Executes the standalone `yamlr verify` command.
pub fn execute_verify(args: &[String]) -> i32 {
    let matches = match crate::cli::support_contract::parse("verify", args) {
        Ok(matches) => matches,
        Err(error) => return crate::cli::report_argument_error(error),
    };
    let target_path = matches.get_one::<String>("target").unwrap().clone();
    let key = matches
        .get_one::<String>("key")
        .cloned()
        .or_else(|| std::env::var("YAMLR_SIGN_KEY").ok())
        .filter(|value| !value.trim().is_empty());

    let key = match key.filter(|value| !value.trim().is_empty()) {
        Some(key) => key,
        None => {
            eprintln!("[ERROR] Verification requires --key <value> or YAMLR_SIGN_KEY.");
            return EXIT_CONFIG_ERROR;
        }
    };

    let p = Path::new(&target_path);
    if !p.exists() {
        eprintln!("[ERROR] Target path '{}' does not exist.", target_path);
        return EXIT_CONFIG_ERROR;
    }

    let mut verified = 0;
    let mut failed = 0;
    let mut unsigned = 0;

    let files: Vec<_> = if p.is_file() {
        vec![p.to_path_buf()]
    } else {
        let mut files = Vec::new();
        for entry in WalkDir::new(p).follow_links(false) {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    eprintln!("[ERROR] Verification traversal failed: {}", error);
                    return EXIT_SYSTEM_ERROR;
                }
            };
            let path = entry.into_path();
            if path.is_file()
                && path
                    .extension()
                    .map_or(false, |ext| ext == "yaml" || ext == "yml")
            {
                files.push(path);
            }
        }
        files
    };

    for file in files {
        let content = match fs::read_to_string(&file) {
            Ok(content) => content,
            Err(error) => {
                eprintln!(
                    "[ERROR] Failed to read manifest '{}': {}",
                    file.display(),
                    error
                );
                return EXIT_SYSTEM_ERROR;
            }
        };
        match extract_manifest_signature(&content) {
            Some(_) => {
                if verify_manifest_hmac(&content, &key) {
                    println!("[VALID]   {}", file.display());
                    verified += 1;
                } else {
                    eprintln!(
                        "[TAMPER]  {} (Signature mismatch / unauthorized mutation!)",
                        file.display()
                    );
                    failed += 1;
                }
            }
            None => {
                println!("[UNSIGNED] {}", file.display());
                unsigned += 1;
            }
        }
    }

    println!("\n=== Manifest Verification Summary ===");
    println!(
        "Verified: {}, Tampered/Failed: {}, Unsigned: {}",
        verified, failed, unsigned
    );

    if failed > 0 {
        EXIT_VIOLATIONS
    } else {
        EXIT_SUCCESS
    }
}
