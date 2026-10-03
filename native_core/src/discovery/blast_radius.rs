//! Multi-Factor Blast Radius Calculator.
//!
//! Why: Assesses the architectural blast radius of any target resource by exploring
//!      its transitive dependency closure, evaluating impact depth, and classifying risk
//!      against ingress, shared data, and security privilege boundaries.

use crate::models::{NativeBlastRadius, NativeEdge};
use std::collections::{HashMap, HashSet, VecDeque};

pub const MAX_TRAVERSAL_DEPTH: usize = 32;

/// Calculates the multi-factor blast radius and transitive impact of a target resource.
pub fn calculate_blast_radius(target_resource: &str, edges: &[NativeEdge]) -> NativeBlastRadius {
    if edges.is_empty() || target_resource.trim().is_empty() {
        return NativeBlastRadius {
            target_resource: target_resource.to_string(),
            impacted_resources: Vec::new(),
            risk_score: 0.0,
            depth: 0,
            risk_level: "LOW".to_string(),
        };
    }

    // 1. Resolve canonical target key (supports full 'Kind/ns/name' or simple 'name')
    let mut canonical_target = target_resource.to_string();
    let mut all_nodes = HashSet::new();

    for edge in edges {
        all_nodes.insert(edge.from_resource.as_str());
        all_nodes.insert(edge.to_resource.as_str());
    }

    if !all_nodes.contains(target_resource) {
        let suffix = format!("/{}", target_resource);
        if let Some(matched) = all_nodes.iter().find(|n| n.ends_with(&suffix)) {
            canonical_target = (*matched).to_string();
        }
    }

    // 2. Build bidirectional adjacency graph for full relational impact
    let mut adj: HashMap<&str, Vec<&str>> = HashMap::new();
    for edge in edges {
        adj.entry(&edge.from_resource)
            .or_default()
            .push(&edge.to_resource);
        adj.entry(&edge.to_resource)
            .or_default()
            .push(&edge.from_resource);
    }

    // 3. BFS Traversal with max-depth guard
    let mut visited: HashSet<&str> = HashSet::new();
    let mut queue: VecDeque<(&str, usize)> = VecDeque::new();
    let mut impacted = Vec::new();
    let mut max_depth = 0;

    visited.insert(&canonical_target);
    queue.push_back((&canonical_target, 0));

    while let Some((curr, depth)) = queue.pop_front() {
        if depth >= MAX_TRAVERSAL_DEPTH {
            continue;
        }

        if let Some(neighbors) = adj.get(curr) {
            for &next_node in neighbors {
                if visited.insert(next_node) {
                    impacted.push(next_node.to_string());
                    let next_depth = depth + 1;
                    if next_depth > max_depth {
                        max_depth = next_depth;
                    }
                    queue.push_back((next_node, next_depth));
                }
            }
        }
    }

    if impacted.is_empty() {
        return NativeBlastRadius {
            target_resource: canonical_target,
            impacted_resources: Vec::new(),
            risk_score: 0.0,
            depth: 0,
            risk_level: "LOW".to_string(),
        };
    }

    // 4. Categorical Impact Assessment
    let has_ingress_impact = impacted.iter().any(|r| {
        r.starts_with("Ingress/") || r.starts_with("HTTPRoute/") || r.starts_with("Gateway/")
    });
    let has_data_impact = impacted.iter().any(|r| {
        r.starts_with("ConfigMap/")
            || r.starts_with("Secret/")
            || r.starts_with("PersistentVolumeClaim/")
    });
    let has_rbac_impact = impacted.iter().any(|r| {
        r.starts_with("ClusterRole/")
            || r.starts_with("ClusterRoleBinding/")
            || r.starts_with("Role/")
            || r.starts_with("RoleBinding/")
            || r.starts_with("ServiceAccount/")
    });

    // 5. Multi-Factor Risk Scoring
    let mut raw_score = (impacted.len() as f64) * 1.2 + (max_depth as f64) * 0.4;
    if has_ingress_impact {
        raw_score += 2.5;
    }
    if has_data_impact {
        raw_score += 1.5;
    }
    if has_rbac_impact {
        raw_score += 1.5;
    }

    let risk_score = ((raw_score.clamp(1.0, 10.0)) * 100.0).round() / 100.0;

    let risk_level = if risk_score >= 7.5 || (has_ingress_impact && impacted.len() >= 3) {
        "CRITICAL"
    } else if risk_score >= 5.0 || has_ingress_impact {
        "HIGH"
    } else if risk_score >= 2.5 {
        "MEDIUM"
    } else {
        "LOW"
    };

    impacted.sort();

    NativeBlastRadius {
        target_resource: canonical_target,
        impacted_resources: impacted,
        risk_score,
        depth: max_depth,
        risk_level: risk_level.to_string(),
    }
}

/// Backward compatibility wrapper for native_calculate_blast_radius.
pub fn native_calculate_blast_radius(
    resource_name: String,
    edges: Vec<NativeEdge>,
) -> NativeBlastRadius {
    calculate_blast_radius(&resource_name, &edges)
}
