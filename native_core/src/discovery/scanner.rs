//! Fleet Filesystem Resource Scanner.
//!
//! Why: High-performance filesystem crawler with anti-DoS fleet size guards,
//!      Windows long-path support, and multi-document YAML identity extraction.

use crate::identity::extract_native_identity;
use crate::models::{NativeDiscoveryResult, NativeIdentity, NativeShard};
use crate::sharder::native_shard;
use std::collections::HashSet;
use std::fs;
#[cfg(windows)]
use std::path::Path;
use walkdir::WalkDir;

/// Maximum number of resources scanned in a single fleet run to guard against out-of-memory.
pub const MAX_FLEET_SIZE: usize = 50_000;

/// Discovers all Kubernetes resources within a directory tree.
pub fn native_discover_resources(root_path: String) -> Result<Vec<NativeDiscoveryResult>, String> {
    let mut results = Vec::new();

    #[cfg(windows)]
    let root = if Path::new(&root_path).is_absolute() && !root_path.starts_with(r"\\?\") {
        format!(r"\\?\{}", root_path)
    } else {
        root_path
    };
    #[cfg(not(windows))]
    let root = root_path;

    for entry in WalkDir::new(root).follow_links(false) {
        let entry =
            entry.map_err(|error| format!("Resource discovery traversal failed: {}", error))?;
        if results.len() >= MAX_FLEET_SIZE {
            return Err(format!(
                "Resource discovery exceeded the {} resource limit.",
                MAX_FLEET_SIZE
            ));
        }

        if entry.file_type().is_file() {
            let path = entry.path().to_string_lossy().into_owned();

            #[cfg(windows)]
            {
                let file_name = entry.file_name().to_string_lossy().to_uppercase();
                let stem = file_name.split('.').next().unwrap_or("");
                let reserved = [
                    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "LPT1", "LPT2",
                    "LPT3",
                ];
                if reserved.contains(&stem) {
                    continue;
                }
            }

            if path.ends_with(".yaml") || path.ends_with(".yml") {
                if path.ends_with(".yamlr.tmp") {
                    continue;
                }

                let content = fs::read_to_string(&path)
                    .map_err(|error| format!("Failed to read manifest '{}': {}", path, error))?;
                let raw_abs = fs::canonicalize(&path)
                    .map(|p| p.to_string_lossy().into_owned())
                    .unwrap_or_else(|_| path.clone());
                #[allow(unused_mut)]
                let mut abs_path = crate::path_utils::normalize_display_path(&raw_abs);

                #[cfg(any(windows, target_os = "macos"))]
                {
                    abs_path = abs_path.to_lowercase();
                }

                let all_shards = native_shard(&content);
                let mut doc_shards = Vec::new();
                let mut file_identities: HashSet<String> = HashSet::new();

                for s in all_shards {
                    if s.is_doc_boundary {
                        if !doc_shards.is_empty() {
                            let identities = extract_identities_recursive(doc_shards.clone());
                            for identity in identities {
                                let id_key = format!(
                                    "{}/{}/{}/{}",
                                    identity.api_version.as_deref().unwrap_or(""),
                                    identity.kind,
                                    identity.namespace,
                                    identity.name
                                );
                                file_identities.insert(id_key);

                                results.push(NativeDiscoveryResult {
                                    file_path: abs_path.clone(),
                                    identity: Some(identity),
                                    shard_count: doc_shards.len(),
                                });
                            }
                            doc_shards.clear();
                        }
                    } else {
                        doc_shards.push(s);
                    }
                }

                if !doc_shards.is_empty() {
                    let identities = extract_identities_recursive(doc_shards.clone());
                    for identity in identities {
                        results.push(NativeDiscoveryResult {
                            file_path: abs_path.clone(),
                            identity: Some(identity),
                            shard_count: doc_shards.len(),
                        });
                    }
                }
            }
        }
    }
    Ok(results)
}

/// Recursively extracts identities from an AST shard slice.
pub fn extract_identities_recursive(shards: Vec<NativeShard>) -> Vec<NativeIdentity> {
    let mut identities = Vec::new();
    if let Some(identity) = extract_native_identity(shards) {
        identities.push(identity);
    }
    identities
}
