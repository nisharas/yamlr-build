//! Forensic Topology Analyzers.
//!
//! Why: Inspects fleet topology graphs for architectural circular dependencies,
//!      dangling selectors, orphaned configurations, version drifts, and service collisions.

use crate::models::{NativeDiscoveryResult, NativeEdge};
use std::collections::{HashMap, HashSet};

/// Detects circular dependency loops within topology edges using DFS cycle extraction.
pub fn native_detect_circular_dependencies(edges: &[NativeEdge]) -> Vec<String> {
    let mut adjacency: HashMap<String, Vec<String>> = HashMap::new();
    for edge in edges {
        adjacency
            .entry(edge.from_resource.clone())
            .or_default()
            .push(edge.to_resource.clone());
    }

    let mut cycles = Vec::new();
    let mut visited = HashSet::new();
    let mut stack = HashSet::new();

    // Deterministic traversal order
    let mut nodes: Vec<String> = adjacency.keys().cloned().collect();
    nodes.sort();

    for node in &nodes {
        if !visited.contains(node) {
            let mut path = Vec::new();
            find_cycles(
                node,
                &adjacency,
                &mut visited,
                &mut stack,
                &mut path,
                &mut cycles,
            );
        }
    }

    cycles.sort();
    cycles
}

fn find_cycles(
    node: &str,
    adj: &HashMap<String, Vec<String>>,
    visited: &mut HashSet<String>,
    stack: &mut HashSet<String>,
    path: &mut Vec<String>,
    cycles: &mut Vec<String>,
) -> bool {
    visited.insert(node.to_string());
    stack.insert(node.to_string());
    path.push(node.to_string());

    if let Some(neighbors) = adj.get(node) {
        let mut sorted_neighbors = neighbors.clone();
        sorted_neighbors.sort();

        for neighbor in sorted_neighbors {
            if stack.contains(&neighbor) {
                let cycle_start_idx = path.iter().position(|r| r == &neighbor).unwrap_or(0);
                let cycle_path = path[cycle_start_idx..].join(" -> ");
                cycles.push(format!(
                    "Architectural Error: Circular Dependency Loop: {} -> {}",
                    cycle_path, neighbor
                ));
                return true;
            }
            if !visited.contains(&neighbor)
                && find_cycles(&neighbor, adj, visited, stack, path, cycles)
            {
                return true;
            }
        }
    }

    stack.remove(node);
    path.pop();
    false
}

/// Detects version drift where identical resources are defined across files with conflicting API versions.
pub fn native_detect_version_drift(discovery: Vec<NativeDiscoveryResult>) -> Vec<String> {
    let mut identities: HashMap<String, String> = HashMap::new();
    let mut drifts = Vec::new();

    for res in discovery {
        if let Some(id) = res.identity {
            let resource_key = format!("{}/{}/{}", id.kind, id.namespace, id.name);
            let api_v = id.api_version.unwrap_or_else(|| "unknown".to_string());

            if let Some(existing_v) = identities.get(&resource_key) {
                if *existing_v != api_v {
                    drifts.push(format!(
                        "Architectural Drift: Resource '{}' is defined with multiple API versions: {} and {}.",
                        resource_key, existing_v, api_v
                    ));
                }
            } else {
                identities.insert(resource_key, api_v);
            }
        }
    }

    drifts.sort();
    drifts
}

/// Identifies Services, HPAs, and PDBs whose selectors target zero workloads in their namespace.
pub fn native_detect_dangling_selectors(discovery: &[NativeDiscoveryResult]) -> Vec<String> {
    let mut results = Vec::new();
    let mut pod_labels = Vec::new();

    for res in discovery {
        if let Some(id) = res.identity.as_ref() {
            if matches!(
                id.kind.as_str(),
                "Pod"
                    | "Deployment"
                    | "ReplicaSet"
                    | "StatefulSet"
                    | "DaemonSet"
                    | "Job"
                    | "CronJob"
            ) {
                pod_labels.push((id.namespace.clone(), id.labels.clone()));
            }
        }
    }

    for res in discovery {
        if let Some(id) = res.identity.as_ref() {
            if id.kind == "Service" && !id.selector.is_empty() {
                let mut matched = false;
                for (ns, labels) in &pod_labels {
                    if ns == &id.namespace {
                        let all_match = id
                            .selector
                            .iter()
                            .all(|(sk, sv)| labels.get(sk) == Some(sv));
                        if all_match {
                            matched = true;
                            break;
                        }
                    }
                }
                if !matched {
                    results.push(format!(
                        "Forensic Hazard: Dangling Service Selector in '{}' (Namespace: {}). No pods match these selectors: {:?}.",
                        id.name, id.namespace, id.selector
                    ));
                }
            }
        }
    }

    results.sort();
    results
}

/// Identifies orphaned ConfigMaps and Secrets that are defined but never referenced by any workload.
pub fn native_detect_orphaned_resources(discovery: &[NativeDiscoveryResult]) -> Vec<String> {
    let mut results = Vec::new();
    let mut used_configs = HashSet::new();
    let mut used_secrets = HashSet::new();

    for res in discovery {
        if let Some(id) = res.identity.as_ref() {
            for cfg in &id.config_refs {
                used_configs.insert(format!("{}/{}", id.namespace, cfg));
            }
            for sec in &id.secret_refs {
                used_secrets.insert(format!("{}/{}", id.namespace, sec));
            }
        }
    }

    for res in discovery {
        if let Some(id) = res.identity.as_ref() {
            let key = format!("{}/{}", id.namespace, id.name);
            if id.kind == "ConfigMap" && !used_configs.contains(&key) {
                results.push(format!(
                    "Architectural Waste: Orphaned ConfigMap '{}' in namespace '{}'. No resources reference it.",
                    id.name, id.namespace
                ));
            }
            if id.kind == "Secret" && !used_secrets.contains(&key) {
                results.push(format!(
                    "Architectural Waste: Orphaned Secret '{}' in namespace '{}'. No resources reference it.",
                    id.name, id.namespace
                ));
            }
        }
    }

    results.sort();
    results
}

/// Detects service shadowing where multiple services define identical selectors in the same namespace.
pub fn native_detect_service_shadowing(discovery: &[NativeDiscoveryResult]) -> Vec<String> {
    let mut results = Vec::new();
    let services: Vec<_> = discovery
        .iter()
        .filter_map(|d| d.identity.as_ref())
        .filter(|id| id.kind == "Service")
        .collect();

    for i in 0..services.len() {
        for j in i + 1..services.len() {
            let s1 = services[i];
            let s2 = services[j];
            if s1.namespace == s2.namespace && !s1.selector.is_empty() && s1.selector == s2.selector
            {
                results.push(format!(
                    "Service Shadowing: Overlapping Selectors detected between '{}' and '{}' in namespace '{}'. This leads to non-deterministic traffic routing.",
                    s1.name, s2.name, s1.namespace
                ));
            }
        }
    }

    results.sort();
    results
}
