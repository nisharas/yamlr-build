use crate::models::*;
#[derive(Debug, Clone)]
pub struct ShieldConfig {
    pub default_namespace: String,
    pub cpu_limit: String,
    pub mem_limit: String,
    pub custom_workload_paths: std::collections::HashMap<String, Vec<Vec<String>>>,
}

impl Default for ShieldConfig {
    fn default() -> Self {
        Self {
            default_namespace: "default".to_string(),
            cpu_limit: "500m".to_string(),
            mem_limit: "512Mi".to_string(),
            custom_workload_paths: std::collections::HashMap::new(),
        }
    }
}

pub fn native_apply_shield(manifest: &mut SemanticManifest, config: &ShieldConfig) -> Vec<String> {
    // Shield Policy Enforcement is opt-in per Feature Scorecard Trust Gate
    let is_enabled = manifest
        .root
        .find_value("metadata.annotations.yamlr.io/shield")
        .map(|v| v.trim().trim_matches('"') == "true" || v.trim().trim_matches('"') == "enabled")
        .unwrap_or(false);

    if !is_enabled {
        return Vec::new();
    }

    let mut changes = Vec::new();
    let indent_step = manifest.indent_step;
    let root = &mut manifest.root;

    // --- POLICY 1: Ensure Namespace ---
    if let Some(msg) = rule_ensure_namespace(root, config, indent_step) {
        changes.push(msg);
    }

    // --- POLICY 2: Inject Resource Limits ---
    if let Some(msg) = rule_inject_resource_limits(root, config, indent_step) {
        changes.push(msg);
    }

    changes
}

fn rule_ensure_namespace(
    root: &mut SemanticNode,
    config: &ShieldConfig,
    indent_step: usize,
) -> Option<String> {
    let kind = root.find_value("kind").unwrap_or_default();
    let cluster_scoped = [
        "Namespace",
        "Node",
        "ClusterRole",
        "ClusterRoleBinding",
        "StorageClass",
    ];

    if kind.is_empty() || cluster_scoped.contains(&kind.as_str()) {
        return None;
    }

    // Proactive Metadata Creation
    if root.find_node("metadata").is_none() {
        root.children.push(SemanticNode {
            key: "metadata".to_string(),
            value: None,
            children: Vec::new(),
            shards: vec![create_ghost_shard(
                root.indent + indent_step,
                "metadata",
                None,
                "S-100",
            )],
            indent: root.indent + indent_step,
            is_empty_flow: false,
        });
    }

    if let Some(metadata) = root.find_node_mut("metadata") {
        if let Some(ns_node) = metadata.find_node_mut("namespace") {
            // Substantive Enforcement
            if ns_node.value.is_none() || ns_node.value.as_ref().unwrap().is_empty() {
                ns_node.value = Some(config.default_namespace.clone());
                return Some(format!(
                    "Action: Enforced 'namespace: {}' on empty field.",
                    config.default_namespace
                ));
            }
        } else {
            let key = "namespace".to_string();
            let value = config.default_namespace.clone();
            let ghost_shard =
                create_ghost_shard(metadata.indent + indent_step, &key, Some(&value), "S-101");

            metadata.children.push(SemanticNode {
                key,
                value: Some(value),
                children: Vec::new(),
                shards: vec![ghost_shard],
                indent: metadata.indent + indent_step,
                is_empty_flow: false,
            });
            return Some(format!(
                "Action: Added 'namespace: {}' policy.",
                config.default_namespace
            ));
        }
    }
    None
}

fn rule_inject_resource_limits(
    root: &mut SemanticNode,
    config: &ShieldConfig,
    indent_step: usize,
) -> Option<String> {
    let kind = root.find_value("kind").unwrap_or_default();

    let workload_paths = match kind.as_str() {
        "Deployment" | "StatefulSet" | "DaemonSet" | "ReplicaSet" => vec![
            vec!["spec", "template", "spec", "containers"],
            vec!["spec", "template", "spec", "initContainers"],
        ],
        "Pod" => vec![vec!["spec", "containers"], vec!["spec", "initContainers"]],
        "Job" => vec![
            vec!["spec", "template", "spec", "containers"],
            vec!["spec", "template", "spec", "initContainers"],
        ],
        "CronJob" => vec![
            vec![
                "spec",
                "jobTemplate",
                "spec",
                "template",
                "spec",
                "containers",
            ],
            vec![
                "spec",
                "jobTemplate",
                "spec",
                "template",
                "spec",
                "initContainers",
            ],
        ],
        _ => return None,
    };

    let mut modified = false;
    for path in workload_paths {
        if let Some(containers_node) = root.find_node_by_path_mut(&path) {
            for container in &mut containers_node.children {
                if inject_limits_to_container(container, config, indent_step) {
                    modified = true;
                }
            }
        }
    }

    if modified {
        return Some(format!(
            "Shield: Injected default resource limits ({}, {}).",
            config.cpu_limit, config.mem_limit
        ));
    }
    None
}

fn inject_limits_to_container(
    container: &mut SemanticNode,
    config: &ShieldConfig,
    indent_step: usize,
) -> bool {
    let resources = if let Some(res) = container.find_node_mut("resources") {
        res
    } else {
        container.children.push(SemanticNode {
            key: "resources".to_string(),
            value: None,
            children: Vec::new(),
            shards: vec![create_ghost_shard(
                container.indent + indent_step,
                "resources",
                None,
                "S-200",
            )],
            indent: container.indent + indent_step,
            is_empty_flow: false,
        });
        container.children.last_mut().unwrap()
    };

    let limits = if let Some(lim) = resources.find_node_mut("limits") {
        lim
    } else {
        resources.children.push(SemanticNode {
            key: "limits".to_string(),
            value: None,
            children: Vec::new(),
            shards: vec![create_ghost_shard(
                resources.indent + indent_step,
                "limits",
                None,
                "S-201",
            )],
            indent: resources.indent + indent_step,
            is_empty_flow: false,
        });
        resources.children.last_mut().unwrap()
    };

    let mut modified = false;

    // Check CPU
    if let Some(cpu_node) = limits.find_node_mut("cpu") {
        if cpu_node.value.is_none() || cpu_node.value.as_ref().unwrap().is_empty() {
            cpu_node.value = Some(config.cpu_limit.clone());
            modified = true;
        }
    } else {
        limits.children.push(SemanticNode {
            key: "cpu".to_string(),
            value: Some(config.cpu_limit.clone()),
            children: Vec::new(),
            shards: vec![create_ghost_shard(
                limits.indent + indent_step,
                "cpu",
                Some(&config.cpu_limit),
                "S-202",
            )],
            indent: limits.indent + indent_step,
            is_empty_flow: false,
        });
        modified = true;
    }

    // Check Memory
    if let Some(mem_node) = limits.find_node_mut("memory") {
        if mem_node.value.is_none() || mem_node.value.as_ref().unwrap().is_empty() {
            mem_node.value = Some(config.mem_limit.clone());
            modified = true;
        }
    } else {
        limits.children.push(SemanticNode {
            key: "memory".to_string(),
            value: Some(config.mem_limit.clone()),
            children: Vec::new(),
            shards: vec![create_ghost_shard(
                limits.indent + indent_step,
                "memory",
                Some(&config.mem_limit),
                "S-203",
            )],
            indent: limits.indent + indent_step,
            is_empty_flow: false,
        });
        modified = true;
    }

    modified
}

fn create_ghost_shard(indent: usize, key: &str, value: Option<&str>, rule_id: &str) -> NativeShard {
    let now = chrono::Local::now();
    NativeShard {
        line_no: 0,
        indent,
        key: key.to_string(),
        value: value.map(|v| v.to_string()),
        is_list_item: false,
        is_doc_boundary: false,
        is_block: false,
        is_flow_style: false,
        raw_line: format!("{}: {}", key, value.unwrap_or("")),
        comment: format!(
            "# [Yamlr:{}] Injected on {}",
            rule_id,
            now.format("%Y-%m-%d")
        ),
        layout_sequence: Vec::new(),
        trailing_layout_sequence: Vec::new(),
        is_table_continuation: false,
        original_indent: indent,
        line_ending: "\n".to_string(),
    }
}
