//! Resource Limits & Requests Sanitizer (Feature 12 of 15).
//!
//! Why: Misconfigured resources cause cluster-wide instability:
//! 1. Flat resources (e.g. `resources: { cpu: 500m }` without `limits`/`requests` wrapper)
//!    are completely ignored by kube-apiserver.
//! 2. Inverted resources (`requests > limits`) cause immediate Pod rejection.
//! 3. Missing limits expose nodes to Out-Of-Memory (OOM) evictions and CPU starvation.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

/// Parses CPU string (e.g. "500m", "1", "2.5") into millicores.
pub fn parse_cpu_millicores(cpu_str: &str) -> Option<i64> {
    let s = cpu_str.trim().trim_matches(|c| c == '\'' || c == '"');
    if s.ends_with('m') {
        s[..s.len() - 1].parse::<i64>().ok()
    } else if let Ok(val) = s.parse::<f64>() {
        Some((val * 1000.0) as i64)
    } else {
        None
    }
}

/// Parses Memory string (e.g. "256Mi", "1Gi", "500M") into megabytes.
pub fn parse_memory_mb(mem_str: &str) -> Option<i64> {
    let s = mem_str.trim().trim_matches(|c| c == '\'' || c == '"');
    if s.ends_with("Gi") {
        s[..s.len() - 2]
            .parse::<f64>()
            .ok()
            .map(|v| (v * 1024.0) as i64)
    } else if s.ends_with("Mi") {
        s[..s.len() - 2].parse::<i64>().ok()
    } else if s.ends_with("Ki") {
        s[..s.len() - 2].parse::<i64>().ok().map(|v| v / 1024)
    } else if s.ends_with('G') {
        s[..s.len() - 1]
            .parse::<f64>()
            .ok()
            .map(|v| (v * 1000.0) as i64)
    } else if s.ends_with('M') {
        s[..s.len() - 1].parse::<i64>().ok()
    } else {
        None
    }
}

/// Normalizes flat resource keys into requests and limits.
pub fn normalize_flat_resources(
    resources_node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if crate::healers::template_masker::contains_dynamic_block(resources_node) {
        return;
    }
    let has_requests = resources_node.find_node("requests").is_some();
    let has_limits = resources_node.find_node("limits").is_some();

    // Check if flat keys exist (e.g. 'cpu', 'memory')
    let mut flat_indices = Vec::new();
    for (i, c) in resources_node.children.iter().enumerate() {
        if c.key == "cpu" || c.key == "memory" {
            flat_indices.push(i);
        }
    }

    if !flat_indices.is_empty() && (!has_requests || !has_limits) {
        let mut flat_children = Vec::new();
        for idx in flat_indices.into_iter().rev() {
            flat_children.push(resources_node.children.remove(idx));
        }

        let mut req_children = flat_children.clone();
        for c in &mut req_children {
            c.indent = resources_node.indent + 4;
        }

        let mut lim_children = flat_children;
        for c in &mut lim_children {
            c.indent = resources_node.indent + 4;
        }

        let requests_node = SemanticNode {
            key: "requests".to_string(),
            value: None,
            indent: resources_node.indent + 2,
            is_empty_flow: false,
            children: req_children,
            shards: Vec::new(),
        };

        let limits_node = SemanticNode {
            key: "limits".to_string(),
            value: None,
            indent: resources_node.indent + 2,
            is_empty_flow: false,
            children: lim_children,
            shards: Vec::new(),
        };

        if !has_requests {
            resources_node.children.push(requests_node);
        }
        if !has_limits {
            resources_node.children.push(limits_node);
        }

        let msg =
            "Remediation [RES-001]: Structured flat resource keys into 'requests' and 'limits'."
                .to_string();
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }
}

/// Detects and corrects inverted requests and limits (requests > limits).
pub fn sanitize_inverted_resources(
    resources_node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let mut swap_cpu = false;
    let mut swap_mem = false;

    let req_cpu_str = resources_node
        .find_node("requests")
        .and_then(|r| r.find_value("cpu"));
    let lim_cpu_str = resources_node
        .find_node("limits")
        .and_then(|l| l.find_value("cpu"));

    if let (Some(r), Some(l)) = (&req_cpu_str, &lim_cpu_str) {
        if let (Some(r_mc), Some(l_mc)) = (parse_cpu_millicores(r), parse_cpu_millicores(l)) {
            if r_mc > l_mc {
                swap_cpu = true;
            }
        }
    }

    let req_mem_str = resources_node
        .find_node("requests")
        .and_then(|r| r.find_value("memory"));
    let lim_mem_str = resources_node
        .find_node("limits")
        .and_then(|l| l.find_value("memory"));

    if let (Some(r), Some(l)) = (&req_mem_str, &lim_mem_str) {
        if let (Some(r_mb), Some(l_mb)) = (parse_memory_mb(r), parse_memory_mb(l)) {
            if r_mb > l_mb {
                swap_mem = true;
            }
        }
    }

    if swap_cpu {
        if let Some(req_node) = resources_node.find_node_mut("requests") {
            if let Some(cpu_node) = req_node.find_node_mut("cpu") {
                cpu_node.value = lim_cpu_str.clone();
            }
        }
        if let Some(lim_node) = resources_node.find_node_mut("limits") {
            if let Some(cpu_node) = lim_node.find_node_mut("cpu") {
                cpu_node.value = req_cpu_str.clone();
            }
        }
        let msg = format!(
            "Remediation [RES-002]: Swapped inverted CPU resources (request '{}' > limit '{}').",
            req_cpu_str.unwrap_or_default(),
            lim_cpu_str.unwrap_or_default()
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }

    if swap_mem {
        if let Some(req_node) = resources_node.find_node_mut("requests") {
            if let Some(mem_node) = req_node.find_node_mut("memory") {
                mem_node.value = lim_mem_str.clone();
            }
        }
        if let Some(lim_node) = resources_node.find_node_mut("limits") {
            if let Some(mem_node) = lim_node.find_node_mut("memory") {
                mem_node.value = req_mem_str.clone();
            }
        }
        let msg = format!(
            "Remediation [RES-002]: Swapped inverted Memory resources (request '{}' > limit '{}').",
            req_mem_str.unwrap_or_default(),
            lim_mem_str.unwrap_or_default()
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }
}

/// Sanitizes resource quantities:
/// Trap 27: Removes spaces inside quantity strings (`512 Mi` -> `512Mi`, `500 m` -> `500m`).
/// Trap 28: Corrects decimal millicores misunderstanding (`0.5m` -> `500m`).
pub fn sanitize_resource_quantities(
    resources_node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    for section_name in ["requests", "limits"] {
        if let Some(section) = resources_node.find_node_mut(section_name) {
            for prop in &mut section.children {
                let raw_val_opt = prop.value.clone();
                if let Some(raw_val) = raw_val_opt {
                    let unquoted = raw_val.trim().trim_matches('"').trim_matches('\'').to_string();

                    // Trap 27: Space inside unit multiplier `512 Mi` -> `512Mi`, `500 m` -> `500m`
                    if unquoted.contains(' ') {
                        let parts: Vec<&str> = unquoted.split_whitespace().collect();
                        if parts.len() == 2 && parts[0].chars().all(|c| c.is_ascii_digit() || c == '.') {
                            let collapsed = format!("{}{}", parts[0], parts[1]);
                            prop.value = Some(format!("\"{}\"", collapsed));
                            let msg = format!(
                                "Remediation [RES-003]: Collapsed whitespace in resource quantity '{}' -> '{}' under {}.{}.",
                                unquoted, collapsed, section_name, prop.key
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                            continue;
                        }
                    }

                    // Trap 28: Decimal millicores misunderstanding `0.5m` -> `500m`
                    if prop.key == "cpu" && unquoted.starts_with("0.") && unquoted.ends_with('m') {
                        if let Ok(fraction) = unquoted[..unquoted.len() - 1].parse::<f64>() {
                            let corrected_millicores = (fraction * 1000.0) as i64;
                            let healed = format!("{}m", corrected_millicores);
                            prop.value = Some(format!("\"{}\"", healed));
                            let msg = format!(
                                "Remediation [RES-004]: Corrected decimal millicores notation '{}' -> '{}' under {}.cpu.",
                                unquoted, healed, section_name
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }
        }
    }
}

/// Primary Entrypoint: Sanitizes and repairs resource limits and requests.
pub fn heal_resource_sanitization(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    for c_node in manifest.root.find_nodes_by_key_recursive_mut("containers") {
        for container in &mut c_node.children {
            if let Some(resources_node) = container.find_node_mut("resources") {
                sanitize_resource_quantities(resources_node, telemetry, &mut changes);
                normalize_flat_resources(resources_node, telemetry, &mut changes);
                sanitize_inverted_resources(resources_node, telemetry, &mut changes);
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_cpu() {
        assert_eq!(parse_cpu_millicores("500m"), Some(500));
        assert_eq!(parse_cpu_millicores("1"), Some(1000));
        assert_eq!(parse_cpu_millicores("2.5"), Some(2500));
    }

    #[test]
    fn test_parse_memory() {
        assert_eq!(parse_memory_mb("256Mi"), Some(256));
        assert_eq!(parse_memory_mb("1Gi"), Some(1024));
    }

    #[test]
    fn test_sanitize_resource_quantities() {
        let mut resources_node = SemanticNode {
            key: "resources".to_string(),
            value: None,
            indent: 4,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![
                SemanticNode {
                    key: "limits".to_string(),
                    value: None,
                    indent: 6,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![
                        SemanticNode {
                            key: "memory".to_string(),
                            value: Some("\"512 Mi\"".to_string()), // Trap 27: space in quantity
                            indent: 8,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: Vec::new(),
                        },
                        SemanticNode {
                            key: "cpu".to_string(),
                            value: Some("\"0.5m\"".to_string()), // Trap 28: decimal millicores typo
                            indent: 8,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: Vec::new(),
                        },
                    ],
                },
            ],
        };

        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();
        sanitize_resource_quantities(&mut resources_node, &mut telemetry, &mut changes);

        assert_eq!(changes.len(), 2);
        let limits = resources_node.find_node("limits").unwrap();
        assert_eq!(limits.find_value("memory"), Some("\"512Mi\"".to_string()));
        assert_eq!(limits.find_value("cpu"), Some("\"500m\"".to_string()));
    }
}
