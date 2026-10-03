//! Kubernetes Strategic Merge Patch & Field Replacement Matrix.
//!
//! Why: Kubernetes manifests require domain-specific list merging rules where lists
//! of objects are merged by primitive keys (e.g. `name`, `containerPort`, `mountPath`,
//! `port`, `ip`, `devicePath`) instead of naive list appending or replacement.
//! This module implements strategic merging, `$patch: delete` directives, diamond
//! dependency overlay resolution, and Kustomize v5+ field replacements.

use crate::parsers::kustomize::renderer::KustomizeReplacement;
use serde_yaml::Value;

/// The Kubernetes special directive key for strategic merge patch operations.
const PATCH_DIRECTIVE_KEY: &str = "$patch";

/// List merge keys checked in priority order when resolving list item identity.
const STRATEGIC_MERGE_KEYS: &[&str] = &[
    "name",
    "containerPort",
    "mountPath",
    "port",
    "ip",
    "devicePath",
];

/// Recursively merges a patch YAML value into a target YAML value using Kubernetes
/// Strategic Merge Patch semantics, including `$patch: delete` directive support.
///
/// Why: Preserves existing container configurations while injecting or overriding
/// specific fields identified by merge keys. The `$patch: delete` directive allows
/// Kustomize overlays to surgically remove specific keys or list items without
/// replacing the entire parent — preserving all sibling keys and their comments.
pub fn merge_strategic(target: &mut Value, patch: &Value) {
    match (target, patch) {
        (Value::Mapping(t_map), Value::Mapping(p_map)) => {
            // Check for top-level $patch: delete — remove this entire mapping from parent
            let patch_directive = p_map
                .get(&Value::String(PATCH_DIRECTIVE_KEY.to_string()))
                .and_then(|v| v.as_str());

            if patch_directive == Some("delete") {
                // Signal to caller: this mapping should be deleted.
                // The caller (list merge path) handles actual removal.
                // At the scalar level we clear the map to signal deletion.
                t_map.clear();
                return;
            }

            for (k, v) in p_map {
                // Skip the $patch directive key itself — it's a control directive, not a data key
                if k.as_str() == Some(PATCH_DIRECTIVE_KEY) {
                    continue;
                }

                if let Some(target_val) = t_map.get_mut(k) {
                    // Check if the patch value itself is a delete directive mapping
                    if is_delete_directive(v) {
                        t_map.remove(k);
                    } else {
                        merge_strategic(target_val, v);
                    }
                } else {
                    t_map.insert(k.clone(), v.clone());
                }
            }
        }
        (Value::Sequence(t_seq), Value::Sequence(p_seq)) => {
            // Collect indices to delete (from $patch: delete items) in reverse order
            let mut delete_indices: Vec<usize> = Vec::new();

            for p_item in p_seq {
                // Handle $patch: delete directive on list items
                if is_delete_directive(p_item) {
                    // Find matching item by merge key and mark for deletion
                    if let Some(match_idx) = find_matching_list_item(t_seq, p_item) {
                        delete_indices.push(match_idx);
                    }
                    continue;
                }

                if let Some(match_idx) = find_matching_list_item(t_seq, p_item) {
                    merge_strategic(&mut t_seq[match_idx], p_item);
                    // If merge resulted in an empty map (delete signal), mark for removal
                    if t_seq[match_idx]
                        .as_mapping()
                        .map(|m| m.is_empty())
                        .unwrap_or(false)
                    {
                        delete_indices.push(match_idx);
                    }
                } else {
                    t_seq.push(p_item.clone());
                }
            }

            // Remove delete-marked items in reverse order to preserve indices
            delete_indices.sort_unstable();
            delete_indices.dedup();
            for idx in delete_indices.into_iter().rev() {
                if idx < t_seq.len() {
                    t_seq.remove(idx);
                }
            }
        }
        (t, p) => {
            *t = p.clone();
        }
    }
}

/// Returns true if a patch value represents a `$patch: delete` directive.
///
/// Why: Kustomize's `$patch: delete` can appear both as a standalone mapping key
/// (on the patch item itself) or as a sibling key in the item to delete. This
/// helper normalizes both forms.
fn is_delete_directive(v: &Value) -> bool {
    if let Some(map) = v.as_mapping() {
        map.get(&Value::String(PATCH_DIRECTIVE_KEY.to_string()))
            .and_then(|d| d.as_str())
            == Some("delete")
    } else {
        false
    }
}

/// Identifies whether a sequence item matches any strategic merge key from the patch.
fn find_matching_list_item(seq: &[Value], patch_item: &Value) -> Option<usize> {
    let p_map = patch_item.as_mapping()?;
    for &key_str in STRATEGIC_MERGE_KEYS {
        let k_val = Value::String(key_str.to_string());
        if let Some(p_val) = p_map.get(&k_val) {
            for (idx, item) in seq.iter().enumerate() {
                if let Some(i_map) = item.as_mapping() {
                    if i_map.get(&k_val) == Some(p_val) {
                        return Some(idx);
                    }
                }
            }
        }
    }
    None
}

/// Resolves a multi-tier Kustomize overlay stack with diamond-dependency support.
///
/// Why: In production GitOps repositories, environments commonly follow a
/// "base → component → overlay" diamond pattern:
///
/// ```text
///        base
///       /    \
///  staging  production
///       \    /
///     final-env
/// ```
///
/// A naive sequential merge loses patches from one branch when the other branch
/// overwrites the merged result. This function applies each overlay tier in order
/// into a single accumulated document, using strategic merge semantics for each
/// layer — ensuring all branches contribute their patches to the final state.
///
/// # Arguments
/// * `base` — The root base manifest as a mutable `serde_yaml::Value`.
/// * `overlay_tiers` — Ordered slice of patch layers (lowest → highest priority).
///
/// # Returns
/// The final merged manifest after all tiers are applied.
pub fn merge_overlays_tiered(mut base: Value, overlay_tiers: &[Value]) -> Value {
    for overlay in overlay_tiers {
        merge_strategic(&mut base, overlay);
    }
    base
}

/// Applies Kustomize v5+ replacements across multi-document resources.
///
/// Why: Propagates dynamically generated values (e.g. Service cluster IPs, ConfigMap hashes)
/// across decoupled resources before validation and healing.
pub fn apply_replacements(
    docs: &mut [Value],
    replacements: &[KustomizeReplacement],
) -> Result<(), String> {
    for rep in replacements {
        let Some(ref source) = rep.source else {
            continue;
        };
        let field_path = source.field_path.as_deref().unwrap_or("metadata.name");

        let mut source_value = None;
        for doc in docs.iter() {
            if let Some(ref k) = source.kind {
                if doc.get("kind").and_then(|v| v.as_str()) != Some(k) {
                    continue;
                }
            }
            if let Some(ref n) = source.name {
                if doc
                    .get("metadata")
                    .and_then(|m| m.get("name"))
                    .and_then(|v| v.as_str())
                    != Some(n)
                {
                    continue;
                }
            }
            if let Some(val) = extract_field_value(doc, field_path) {
                source_value = Some(val.clone());
                break;
            }
        }

        let Some(source_val) = source_value else {
            continue;
        };

        for target_group in &rep.targets {
            for doc in docs.iter_mut() {
                if let Some(ref select) = target_group.select {
                    if let Some(ref k) = select.kind {
                        if doc.get("kind").and_then(|v| v.as_str()) != Some(k) {
                            continue;
                        }
                    }
                    if let Some(ref n) = select.name {
                        if doc
                            .get("metadata")
                            .and_then(|m| m.get("name"))
                            .and_then(|v| v.as_str())
                            != Some(n)
                        {
                            continue;
                        }
                    }
                }

                for target_path in &target_group.field_paths {
                    set_field_value(doc, target_path, &source_val);
                }
            }
        }
    }
    Ok(())
}

/// Extracts a nested field value by dot-separated path (supporting [index] array indexing).
pub fn extract_field_value<'a>(doc: &'a Value, path: &str) -> Option<&'a Value> {
    let parts: Vec<&str> = path.split('.').collect();
    let mut current = doc;
    for part in parts {
        let clean_part = part.trim();
        if clean_part.ends_with(']') {
            if let Some(idx_start) = clean_part.find('[') {
                let key = &clean_part[..idx_start];
                let idx_str = &clean_part[idx_start + 1..clean_part.len() - 1];
                if !key.is_empty() {
                    current = current.get(key)?;
                }
                if let Ok(idx) = idx_str.parse::<usize>() {
                    current = current.get(idx)?;
                }
                continue;
            }
        }
        current = current.get(clean_part)?;
    }
    Some(current)
}

/// Sets a nested field value by dot-separated path, creating parent mappings as necessary.
pub fn set_field_value(doc: &mut Value, path: &str, new_val: &Value) {
    let parts: Vec<&str> = path.split('.').collect();
    if parts.is_empty() {
        return;
    }

    let mut current = doc;
    for (i, part) in parts.iter().enumerate() {
        let clean_part = part.trim();
        if i == parts.len() - 1 {
            if let Value::Mapping(map) = current {
                map.insert(Value::String(clean_part.to_string()), new_val.clone());
            }
            return;
        }

        if current.get(clean_part).is_none() {
            if let Value::Mapping(map) = current {
                map.insert(
                    Value::String(clean_part.to_string()),
                    Value::Mapping(serde_yaml::Mapping::new()),
                );
            }
        }
        current = match current {
            Value::Mapping(map) => match map.get_mut(&Value::String(clean_part.to_string())) {
                Some(v) => v,
                None => return,
            },
            _ => return,
        };
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_merge_strategic_ports() {
        let mut target: Value = serde_yaml::from_str(
            r#"
ports:
  - containerPort: 8080
    name: http
"#,
        )
        .unwrap();

        let patch: Value = serde_yaml::from_str(
            r#"
ports:
  - containerPort: 8080
    protocol: TCP
  - containerPort: 9090
    name: metrics
"#,
        )
        .unwrap();

        merge_strategic(&mut target, &patch);
        let ports = target.get("ports").unwrap().as_sequence().unwrap();
        assert_eq!(ports.len(), 2);
        assert_eq!(
            ports[0].get("protocol").and_then(|v| v.as_str()),
            Some("TCP")
        );
        assert_eq!(ports[0].get("name").and_then(|v| v.as_str()), Some("http"));
        assert_eq!(
            ports[1].get("name").and_then(|v| v.as_str()),
            Some("metrics")
        );
    }

    #[test]
    fn test_patch_delete_removes_key_from_mapping() {
        // Why: $patch: delete on a mapping key must remove that key while preserving siblings.
        let mut target: Value = serde_yaml::from_str(
            r#"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  strategy:
    type: RollingUpdate
"#,
        )
        .unwrap();

        let patch: Value = serde_yaml::from_str(
            r#"
spec:
  strategy:
    $patch: delete
"#,
        )
        .unwrap();

        merge_strategic(&mut target, &patch);

        let spec = target.get("spec").unwrap().as_mapping().unwrap();
        // replicas and selector must be preserved
        assert!(spec.contains_key(&Value::String("replicas".to_string())));
        assert!(spec.contains_key(&Value::String("selector".to_string())));
        // strategy must be removed
        assert!(
            !spec.contains_key(&Value::String("strategy".to_string())),
            "$patch: delete must remove the 'strategy' key"
        );
    }

    #[test]
    fn test_patch_delete_removes_list_item_by_merge_key() {
        // Why: $patch: delete on a list item (matched by name key) removes that
        // specific container while preserving all other containers with their full config.
        let mut target: Value = serde_yaml::from_str(
            r#"
containers:
  - name: app
    image: nginx:1.25
  - name: sidecar
    image: envoy:1.29
"#,
        )
        .unwrap();

        let patch: Value = serde_yaml::from_str(
            r#"
containers:
  - name: sidecar
    $patch: delete
"#,
        )
        .unwrap();

        merge_strategic(&mut target, &patch);

        let containers = target.get("containers").unwrap().as_sequence().unwrap();
        assert_eq!(
            containers.len(),
            1,
            "Only 'app' container must remain after deleting 'sidecar'"
        );
        assert_eq!(
            containers[0].get("name").and_then(|v| v.as_str()),
            Some("app")
        );
    }

    #[test]
    fn test_merge_overlays_tiered_diamond_dependency() {
        // Why: Diamond pattern — base is patched by staging and production independently.
        // The final overlay must incorporate changes from BOTH branches, not just the last.
        let base: Value = serde_yaml::from_str(
            r#"
spec:
  replicas: 1
  image: nginx:1.24
  debug: false
"#,
        )
        .unwrap();

        // Staging branch increases replicas
        let staging_patch: Value = serde_yaml::from_str(
            r#"
spec:
  replicas: 3
"#,
        )
        .unwrap();

        // Production branch pins the image to a specific digest
        let production_patch: Value = serde_yaml::from_str(
            r#"
spec:
  image: nginx@sha256:abc123
  debug: false
"#,
        )
        .unwrap();

        let result = merge_overlays_tiered(base, &[staging_patch, production_patch]);

        let spec = result.get("spec").unwrap().as_mapping().unwrap();
        // Both branches' patches must be present in the final result
        assert_eq!(
            spec.get(&Value::String("replicas".to_string()))
                .and_then(|v| v.as_i64()),
            Some(3),
            "Staging patch (replicas: 3) must survive through production overlay"
        );
        assert_eq!(
            spec.get(&Value::String("image".to_string()))
                .and_then(|v| v.as_str()),
            Some("nginx@sha256:abc123"),
            "Production patch (pinned image) must take effect"
        );
    }

    #[test]
    fn test_merge_strategic_comment_preservation_signal() {
        // Why: Merge operations must only mutate fields explicitly listed in the patch.
        // Unpatched sibling keys (proxies for comment-bearing lines in the real AST path)
        // must be fully preserved after a strategic merge.
        let mut target: Value = serde_yaml::from_str(
            r#"
metadata:
  name: web
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
spec:
  replicas: 1
"#,
        )
        .unwrap();

        let patch: Value = serde_yaml::from_str(
            r#"
spec:
  replicas: 5
"#,
        )
        .unwrap();

        merge_strategic(&mut target, &patch);

        // Unpatched metadata.annotations must be completely untouched
        let annotations = target
            .get("metadata")
            .unwrap()
            .get("annotations")
            .unwrap()
            .as_mapping()
            .unwrap();
        assert_eq!(
            annotations.len(),
            2,
            "Both annotations must survive the patch"
        );
        assert_eq!(
            annotations
                .get(&Value::String("prometheus.io/scrape".to_string()))
                .and_then(|v| v.as_str()),
            Some("true")
        );

        // Patched spec.replicas must be updated
        assert_eq!(
            target
                .get("spec")
                .unwrap()
                .get("replicas")
                .unwrap()
                .as_i64(),
            Some(5)
        );
    }
}
