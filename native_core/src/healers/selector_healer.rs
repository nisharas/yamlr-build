//! Service-to-Workload Selector Alignment Engine (Feature 4 of 15).
//!
//! Why: Service selector typos and label drift (e.g. Service `selector: { app: web-api }`
//! vs Deployment `labels: { app: web-service }`) cause 0-endpoint silent traffic blackholes
//! and 503 outages.
//!
//! This module computes cross-resource label similarity, fuzzy matches selector keys/values
//! against target workload labels, and aligns selectors to prevent traffic dropping.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;
use std::collections::HashMap;

pub static WORKLOAD_KINDS: &[&str] = &[
    "Deployment",
    "StatefulSet",
    "DaemonSet",
    "Pod",
    "ReplicaSet",
    "Job",
];

/// Computes string similarity ratio between 0.0 and 1.0 using Levenshtein distance.
pub fn similarity_ratio(s1: &str, s2: &str) -> f64 {
    if s1 == s2 {
        return 1.0;
    }
    let max_len = s1.len().max(s2.len());
    if max_len == 0 {
        return 1.0;
    }
    let dist = crate::healers::typo_healer::levenshtein(s1, s2);
    (max_len as f64 - dist as f64) / max_len as f64
}

/// Calculates label similarity score (0.0 to 1.0) between a selector and workload labels.
pub fn calculate_label_similarity(
    selector: &HashMap<String, String>,
    labels: &HashMap<String, String>,
) -> f64 {
    if selector.is_empty() || labels.is_empty() {
        return 0.0;
    }

    let mut total_score = 0.0;
    for (sk, sv) in selector {
        if let Some(lv) = labels.get(sk) {
            if lv == sv {
                total_score += 1.0;
            } else {
                total_score += similarity_ratio(sv, lv) * 0.8;
            }
        } else {
            // Check for key typos in labels
            let mut best_key_sim = 0.0;
            let mut matched_val = "";
            for (lk, lv) in labels {
                let k_sim = similarity_ratio(sk, lk);
                if k_sim > best_key_sim {
                    best_key_sim = k_sim;
                    matched_val = lv;
                }
            }
            if best_key_sim >= 0.7 {
                let v_sim = similarity_ratio(sv, matched_val);
                total_score += best_key_sim * v_sim * 0.7;
            }
        }
    }

    total_score / selector.len() as f64
}

/// Suggests an aligned selector map given current selector and target workload labels.
pub fn suggest_aligned_selector(
    selector: &HashMap<String, String>,
    labels: &HashMap<String, String>,
) -> HashMap<String, String> {
    let mut aligned = HashMap::new();

    for (sk, sv) in selector {
        if let Some(lv) = labels.get(sk) {
            aligned.insert(sk.clone(), lv.clone());
        } else {
            // Find fuzzy matching key in target labels
            let mut best_key: Option<&String> = None;
            let mut best_sim = 0.0;
            for lk in labels.keys() {
                let sim = similarity_ratio(sk, lk);
                if sim >= 0.65 && sim > best_sim {
                    best_sim = sim;
                    best_key = Some(lk);
                }
            }

            if let Some(bk) = best_key {
                aligned.insert(bk.clone(), labels[bk].clone());
            } else {
                aligned.insert(sk.clone(), sv.clone());
            }
        }
    }

    aligned
}

/// Aligns a Service's `spec.selector` node with given target labels.
pub fn align_service_selector_node(
    spec: &mut SemanticNode,
    aligned_selector: &HashMap<String, String>,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
    target_name: &str,
) {
    if let Some(selector_node) = spec.find_node_mut("selector") {
        let mut modified = false;

        for child in &mut selector_node.children {
            if let Some(new_val) = aligned_selector.get(&child.key) {
                if child.value.as_deref() != Some(new_val) {
                    let old_val = child.value.clone().unwrap_or_default();
                    child.value = Some(new_val.clone());
                    for shard in &mut child.shards {
                        shard.value = Some(new_val.clone());
                    }
                    let msg = format!(
                        "Remediation [REL-011]: Aligned Service selector '{}: {}' -> '{}' to match workload '{}'.",
                        child.key, old_val, new_val, target_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                    modified = true;
                }
            }
        }

        // If key itself changed (e.g. 'appl' -> 'app')
        for (ak, av) in aligned_selector {
            if !selector_node.children.iter().any(|c| c.key == *ak) {
                // Find and rename closest matching child key
                let mut best_idx = None;
                let mut best_sim = 0.0;
                for (idx, c) in selector_node.children.iter().enumerate() {
                    let sim = similarity_ratio(&c.key, ak);
                    if sim >= 0.65 && sim > best_sim {
                        best_sim = sim;
                        best_idx = Some(idx);
                    }
                }
                if let Some(idx) = best_idx {
                    let old_key = selector_node.children[idx].key.clone();
                    selector_node.children[idx].key = ak.clone();
                    selector_node.children[idx].value = Some(av.clone());
                    for shard in &mut selector_node.children[idx].shards {
                        shard.key = ak.clone();
                        shard.value = Some(av.clone());
                    }
                    let msg = format!(
                        "Remediation [REL-011]: Aligned Service selector key '{}: ...' -> '{}: {}' to match workload '{}'.",
                        old_key, ak, av, target_name
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                    modified = true;
                }
            }
        }

        if !modified && !aligned_selector.is_empty() && selector_node.children.is_empty() {
            // Empty selector recovery: populate primary selector label
            for (ak, av) in aligned_selector {
                selector_node.children.push(SemanticNode {
                    key: ak.clone(),
                    value: Some(av.clone()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: selector_node.indent + 2,
                    is_empty_flow: false,
                });
                let msg = format!(
                    "Remediation [REL-011]: Injected missing Service selector '{}: {}' for target workload '{}'.",
                    ak, av, target_name
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }
}

/// Primary Entrypoint: Aligns Service selectors using known workload identities.
pub fn heal_service_selectors_with_identities(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Service" {
        return changes;
    }

    let svc_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_default();
    let svc_ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let mut current_selector = HashMap::new();
    if let Some(spec) = manifest.root.find_node("spec") {
        if let Some(sel) = spec.find_node("selector") {
            for child in &sel.children {
                if let Some(val) = &child.value {
                    current_selector.insert(child.key.clone(), val.clone());
                }
            }
        }
    }

    // Filter relevant workloads
    let workloads: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| WORKLOAD_KINDS.contains(&id.kind.as_str()) && id.namespace == svc_ns)
        .collect();

    // Check if selector already matches any workload
    let already_matches = workloads.iter().any(|w| {
        !current_selector.is_empty()
            && current_selector
                .iter()
                .all(|(k, v)| w.labels.get(k) == Some(v))
    });
    if already_matches {
        return changes;
    }

    // Find best target workload:
    // 1. By exact or prefix name match
    let mut best_target = workloads.iter().find(|w| w.name == svc_name);
    if best_target.is_none() {
        best_target = workloads
            .iter()
            .find(|w| svc_name.starts_with(&w.name) || w.name.starts_with(&svc_name));
    }

    // 2. By highest label similarity
    if best_target.is_none() && !current_selector.is_empty() {
        let mut best_score = 0.50; // minimum threshold
        for w in &workloads {
            let score = calculate_label_similarity(&current_selector, &w.labels);
            if score > best_score {
                best_score = score;
                best_target = Some(w);
            }
        }
    }

    if let Some(target) = best_target {
        if !target.labels.is_empty() {
            let aligned = suggest_aligned_selector(&current_selector, &target.labels);
            if let Some(spec) = manifest.root.find_node_mut("spec") {
                align_service_selector_node(spec, &aligned, telemetry, &mut changes, &target.name);
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_similarity_ratio() {
        assert!((similarity_ratio("payment-api", "payment-api") - 1.0).abs() < 1e-6);
        assert!(similarity_ratio("payment-api", "payment-ap") > 0.85);
    }

    #[test]
    fn test_suggest_aligned_selector() {
        let mut selector = HashMap::new();
        selector.insert("app".to_string(), "payment-ap".to_string());

        let mut labels = HashMap::new();
        labels.insert("app".to_string(), "payment-api".to_string());
        labels.insert("version".to_string(), "v1".to_string());

        let aligned = suggest_aligned_selector(&selector, &labels);
        assert_eq!(aligned.get("app"), Some(&"payment-api".to_string()));
    }
}
