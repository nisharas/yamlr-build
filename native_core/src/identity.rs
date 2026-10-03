use crate::models::{NativeIdentity, NativeRelationship, NativeShard, RelationshipType};
use crate::sharder::native_find_shard_by_path;
use std::collections::HashMap;

pub mod extractors;
pub use extractors::*;

pub fn extract_native_identity(shards: Vec<NativeShard>) -> Option<NativeIdentity> {
    extract_native_identity_ref(&shards)
}

pub fn extract_native_identity_ref(shards: &[NativeShard]) -> Option<NativeIdentity> {
    if shards.is_empty() {
        return None;
    }
    // [HARDENING] Discover root indentation dynamically (handles indented YAML / multi-doc streams)
    let min_indent = shards.iter().map(|s| s.indent).min().unwrap_or(0);

    // [HARDENING] Case-Fuzzy Matching for core K8s fields
    let mut kind: Option<String> = None;
    let mut api_version: Option<String> = None;
    let mut name = None;
    let mut namespace = Some("default".to_string());

    for s in shards {
        let key_lower = s.key.to_lowercase();

        // Core Typo Resilience (Distance-1)
        let is_kind = key_lower == "kind" || key_lower == "kins" || key_lower == "knd";
        let is_api =
            key_lower == "apiversion" || key_lower == "apivrsion" || key_lower == "apiverson";

        if is_kind && s.indent == min_indent {
            kind = s.value.clone();
        } else if is_api && s.indent == min_indent {
            if let Some(val) = &s.value {
                api_version = Some(val.clone());
            }
        }
    }

    // We need at least Kind to proceed
    let kind = kind?;

    // Use path resolver for metadata (hardened)
    if let Some(idx) = native_find_shard_by_path(shards, "metadata.name") {
        name = shards[idx].value.clone();
    }
    if let Some(idx) = native_find_shard_by_path(shards, "metadata.namespace") {
        namespace = shards[idx].value.clone();
    }

    // If we can't find name via strict path, try fuzzy metadata
    if name.is_none() {
        let mut in_metadata = false;
        for s in shards {
            if s.key.to_lowercase() == "metadata" && s.indent == min_indent {
                in_metadata = true;
                continue;
            }
            if in_metadata && s.indent > min_indent {
                if s.key.to_lowercase() == "name" {
                    name = s.value.clone();
                }
                if s.key.to_lowercase() == "namespace" {
                    namespace = s.value.clone();
                }
            } else if s.indent <= min_indent {
                in_metadata = false;
            }
        }
    }

    let name = normalize_identity_segment(name?);
    let namespace = normalize_identity_segment(namespace.unwrap_or_else(|| "default".to_string()));

    let mut labels: HashMap<String, String> = HashMap::new();
    let mut selector: HashMap<String, String> = HashMap::new();

    let mut stack: Vec<(usize, String)> = Vec::new();
    for s in shards {
        while !stack.is_empty() && stack.last().unwrap().0 >= s.indent {
            stack.pop();
        }

        let segment = if s.is_list_item {
            format!("[0].{}", s.key)
        } else {
            s.key.clone()
        };
        let parent_path = stack.last().map(|(_, p)| p.as_str()).unwrap_or("");
        let current_path = if parent_path.is_empty() {
            segment
        } else {
            format!("{}.{}", parent_path, segment)
        };

        if current_path.contains("metadata.labels") && !s.key.is_empty() && s.value.is_some() {
            labels.insert(s.key.clone(), s.value.clone().unwrap());
        }
        if current_path.contains("spec.selector") && !s.key.is_empty() && s.value.is_some() {
            selector.insert(s.key.clone(), s.value.clone().unwrap());
        }

        if s.value.is_none() || s.is_block {
            stack.push((s.indent, current_path.clone()));
        }
    }

    let mut config_refs = Vec::new();
    let mut secret_refs = Vec::new();
    let mut volume_refs = Vec::new();

    for s in shards.iter() {
        let k_lower = s.key.to_lowercase();
        // Context-Deep Dependency Auditing
        if k_lower == "configmapname" || k_lower == "configmap" {
            if let Some(v) = &s.value {
                config_refs.push(v.clone());
            }
        }
        if k_lower == "secretname" || k_lower == "secret" {
            if let Some(v) = &s.value {
                secret_refs.push(v.clone());
            }
        }
        if k_lower == "claimname" || k_lower == "persistentvolumeclaim" {
            if let Some(v) = &s.value {
                volume_refs.push(v.clone());
            }
        }
    }

    let mut owner_refs = Vec::new();
    if native_find_shard_by_path(shards, "metadata.ownerReferences").is_some() {
        owner_refs.push("MANAGED".to_string());
    }

    // Scope-Aware Identity Normalization
    let cluster_scoped_kinds = [
        "ClusterRole",
        "ClusterRoleBinding",
        "Namespace",
        "Node",
        "PersistentVolume",
        "StorageClass",
        "CustomResourceDefinition",
    ];
    let final_namespace = if cluster_scoped_kinds.contains(&kind.as_str()) {
        "__cluster_scoped__".to_string()
    } else if namespace.is_empty() {
        "default".to_string()
    } else {
        namespace
    };

    // Shadow-Aware Identity Normalization
    let mut label_keys: Vec<_> = labels.keys().collect();
    label_keys.sort();
    let label_str: String = label_keys
        .iter()
        .map(|k| format!("{}={}", k, labels.get(*k).unwrap_or(&"".to_string())))
        .collect::<Vec<_>>()
        .join(",");
    let shadow_fingerprint = format!("{}:{}:[{}]", final_namespace, name, label_str);

    let mut relationships = Vec::new();
    let mut ports = Vec::new();

    // Relationship & Port Extraction
    for s in shards.iter() {
        let k_lower = s.key.to_lowercase();

        // 1. Workload Port Extraction
        if k_lower == "containerport" {
            if let Some(val) = &s.value {
                if let Ok(p) = val.parse::<i32>() {
                    ports.push(p);
                }
            }
        }

        // 2. Service targetPort Extraction
        if k_lower == "targetport" {
            if let Some(val) = &s.value {
                if let Ok(p) = val.parse::<i32>() {
                    ports.push(p);
                }
            }
        }

        // 3. ConfigMap / Secret Consumption
        if k_lower == "configmapref" || k_lower == "configmapkeyref" {
            if let Some(name) = &s.value {
                relationships.push(NativeRelationship {
                    rel_type: RelationshipType::CONSUMES,
                    target_kind: "ConfigMap".to_string(),
                    target_name: name.clone(),
                    target_namespace: Some(final_namespace.clone()),
                });
            }
        }

        if k_lower == "secretref" || k_lower == "secretkeyref" {
            if let Some(name) = &s.value {
                relationships.push(NativeRelationship {
                    rel_type: RelationshipType::CONSUMES,
                    target_kind: "Secret".to_string(),
                    target_name: name.clone(),
                    target_namespace: Some(final_namespace.clone()),
                });
            }
        }
    }

    let mut identity = NativeIdentity {
        kind,
        api_version,
        name,
        namespace: final_namespace,
        owner_refs,
        labels,
        selector,
        config_refs,
        secret_refs,
        volume_refs,
        service_refs: vec![],
        role_refs: vec![],
        cluster_role_refs: vec![],
        service_account: None,
        shadow_fingerprint,
        relationships,
        ports,
        annotations: HashMap::new(),
        container_images: Vec::new(),
        container_envs: HashMap::new(),
        security_context: HashMap::new(),
        container_port_defs: Vec::new(),
        replicas: None,
    };

    // Dispatch all 21 modular extractors
    extractors::run_all_extractors(shards, &mut identity);

    Some(identity)
}

fn normalize_identity_segment(val: String) -> String {
    let trimmed = val.trim();
    let mut normalized = trimmed.replace("//", "/");
    while normalized.starts_with("./") {
        normalized = normalized[2..].to_string();
    }
    normalized.trim_matches('/').to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_native_identity_basic() {
        let shards = crate::sharder::native_shard(
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: web\n  namespace: default",
        );
        let id = extract_native_identity(shards).unwrap();
        assert_eq!(id.kind, "Pod");
        assert_eq!(id.name, "web");
        assert_eq!(id.namespace, "default");
    }

    #[test]
    fn test_identity_typo_resilience() {
        let shards =
            crate::sharder::native_shard("apivrsion: v1\nkins: Pod\nmetadata:\n  name: web");
        let id = extract_native_identity(shards).unwrap();
        assert_eq!(id.kind, "Pod");
        assert_eq!(id.api_version, Some("v1".to_string()));
    }

    #[test]
    fn test_cluster_scoped_identity() {
        let shards = crate::sharder::native_shard("kind: ClusterRole\nmetadata:\n  name: admin");
        let id = extract_native_identity(shards).unwrap();
        assert_eq!(id.namespace, "__cluster_scoped__");
    }

    #[test]
    fn test_normalize_identity_segment() {
        assert_eq!(normalize_identity_segment(" ./web/ ".to_string()), "web");
        assert_eq!(normalize_identity_segment("///web///".to_string()), "web");
    }

    #[test]
    fn test_namespace_defaults() {
        let shards = crate::sharder::native_shard("kind: Pod\nmetadata:\n  name: default-ns");
        let id = extract_native_identity(shards).unwrap();
        assert_eq!(id.namespace, "default");
    }

    #[test]
    fn test_label_selector_extraction() {
        let shards = crate::sharder::native_shard("kind: Pod\nmetadata:\n  name: web\n  labels:\n    app: web\nspec:\n  selector:\n    matchLabels:\n      app: web");
        let id = extract_native_identity(shards).unwrap();
        assert_eq!(id.labels.get("app"), Some(&"web".to_string()));
    }

    #[test]
    fn test_configmap_secret_refs() {
        let shards = crate::sharder::native_shard("kind: Pod\nmetadata:\n  name: web\nspec:\n  containers:\n    - envFrom:\n        - configMapRef: app-config\n        - secretRef: app-secret");
        let id = extract_native_identity(shards).unwrap();
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "ConfigMap" && r.target_name == "app-config"));
        assert!(id
            .relationships
            .iter()
            .any(|r| r.target_kind == "Secret" && r.target_name == "app-secret"));
    }

    #[test]
    fn test_shadow_fingerprint_determinism() {
        let shards1 = crate::sharder::native_shard(
            "kind: Pod\nmetadata:\n  name: web\n  labels:\n    a: \"1\"\n    b: \"2\"",
        );
        let shards2 = crate::sharder::native_shard(
            "kind: Pod\nmetadata:\n  name: web\n  labels:\n    b: \"2\"\n    a: \"1\"",
        );
        let id1 = extract_native_identity(shards1).unwrap();
        let id2 = extract_native_identity(shards2).unwrap();
        assert_eq!(id1.shadow_fingerprint, id2.shadow_fingerprint);
    }

    #[test]
    fn test_indented_manifest_identity_extraction() {
        let manifest = "    apiVersion: v1\n    kind: Service\n    metadata:\n      name: backend-svc\n      namespace: prod";
        let shards = crate::sharder::native_shard(manifest);
        let id =
            extract_native_identity(shards).expect("Must extract identity from indented manifest");
        assert_eq!(id.kind, "Service");
        assert_eq!(id.name, "backend-svc");
        assert_eq!(id.namespace, "prod");
    }
}
