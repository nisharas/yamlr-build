//! Topological priority ordering and workspace identity pre-indexing for manifests.

use std::path::Path;
use crate::models::NativeIdentity;
use crate::sharder::native_shard;

/// Assigns topological apply priority to Kubernetes resource kinds.
/// Lower numbers MUST be applied before higher numbers in kubectl apply streams.
pub fn get_manifest_apply_priority(content: &str) -> u8 {
    let shards = native_shard(content);
    let kind = crate::identity::extract_native_identity_ref(&shards)
        .map(|id| id.kind)
        .unwrap_or_default();

    if kind.is_empty() {
        return 0; // Preamble/header comments must stay at the very top of the file
    }

    match kind.as_str() {
        "Namespace" | "CustomResourceDefinition" => 1,
        "ServiceAccount" => 2,
        "ClusterRole" | "Role" | "ClusterRoleBinding" | "RoleBinding" => 3,
        "ConfigMap" | "Secret" | "StorageClass" | "PersistentVolumeClaim" => 4,
        "Deployment" | "StatefulSet" | "DaemonSet" | "Job" | "CronJob" | "Pod" => 5,
        "Service" | "Ingress" | "NetworkPolicy" | "Gateway" | "HTTPRoute" => 6,
        _ => 7,
    }
}

/// Checks if a multi-document stream has an inverted dependency order (e.g. CR before CRD).
/// Only true foundational ordering hazards (CRD or Namespace defined late) justify re-ordering.
pub fn has_critical_topological_inversion(docs: &[String]) -> bool {
    let mut found_non_foundational = false;
    for doc in docs {
        let prio = get_manifest_apply_priority(doc);
        if prio == 0 {
            continue; // Preamble header comments are not workloads
        }
        if prio == 1 && found_non_foundational {
            return true;
        }
        if prio > 1 {
            found_non_foundational = true;
        }
    }
    false
}

/// Pre-indexes resource identities across a workspace or directory to enable cross-file reference resolution.
pub(crate) fn index_workspace_identities(path: &Path) -> Vec<NativeIdentity> {
    let search_path = if path.is_file() {
        path.parent()
            .map(|p| {
                if p.as_os_str().is_empty() {
                    ".".to_string()
                } else {
                    p.to_string_lossy().into_owned()
                }
            })
            .unwrap_or_else(|| ".".to_string())
    } else {
        path.to_string_lossy().into_owned()
    };

    crate::discovery::native_discover_resources(search_path)
        .map(|discovery| discovery.into_iter().filter_map(|d| d.identity).collect())
        .unwrap_or_default()
}
