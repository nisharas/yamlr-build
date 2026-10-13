//! Structural Normalization & Misnested Field Lifter (Feature 3 of 15).
//!
//! Why: Kubernetes manifest authors frequently suffer indentation errors where:
//! 1. Container properties (`ports`, `resources`, `probes`, `volumeMounts`) are
//!    accidentally placed inside `envFrom` list items.
//! 2. `configMapRef` / `secretRef` have `name` misnested as a sibling rather than child.
//! 3. `volumes:` is accidentally indented inside `containers:` instead of `spec:`.
//! 4. Sequence fields (like `containers`, `ports`, `volumeMounts`) are written as
//!    single mappings instead of lists (e.g. `containers:\n  name: x` without `- `).
//!
//! This module deterministically lifts and repairs structural errors to prevent
//! silent schema rejections by kube-apiserver.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub static MISNESTED_CONTAINER_KEYS: &[&str] = &[
    "ports",
    "resources",
    "livenessProbe",
    "readinessProbe",
    "startupProbe",
    "securityContext",
    "volumeMounts",
    "imagePullPolicy",
    "lifecycle",
    "terminationMessagePath",
    "terminationMessagePolicy",
];

pub static FORCED_ARRAY_FIELDS: &[&str] = &[
    "containers",
    "initContainers",
    "volumes",
    "volumeMounts",
    "ports",
    "imagePullSecrets",
    "rules",
    "env",
];

/// Helper: Recursively find mutable references to all Pod spec nodes.
fn find_pod_specs_mut(node: &mut SemanticNode) -> Vec<&mut SemanticNode> {
    let mut pod_specs = Vec::new();

    // Check if this node itself is a Pod spec (contains 'containers')
    let is_pod_spec = node.children.iter().any(|c| c.key == "containers");
    if is_pod_spec {
        pod_specs.push(node);
        return pod_specs;
    }

    // Otherwise traverse template or spec
    for child in &mut node.children {
        if child.key == "spec" || child.key == "template" || child.key == "jobTemplate" {
            pod_specs.extend(find_pod_specs_mut(child));
        }
    }

    pod_specs
}

/// Coerces a specific named child field from an object into an array if written as a single mapping.
pub fn coerce_field_if_mapping(
    parent: &mut SemanticNode,
    field_name: &str,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    if let Some(child) = parent.find_node_mut(field_name) {
        if !child.children.is_empty() {
            let is_already_list = child.children.iter().any(|c| {
                c.key == "-"
                    || c.shards.first().map_or(false, |s| s.is_list_item)
                    || c.children
                        .iter()
                        .any(|gc| gc.shards.first().map_or(false, |s| s.is_list_item))
            });
            if !is_already_list {
                let existing_children = std::mem::take(&mut child.children);
                let list_item = SemanticNode {
                    key: "-".to_string(),
                    value: None,
                    children: existing_children,
                    shards: Vec::new(),
                    indent: child.indent + 2,
                    is_empty_flow: false,
                };
                child.children.push(list_item);

                let msg = format!(
                    "Remediation [STRUCT-005]: Coerced mapping for '{}' into required Kubernetes sequence (list).",
                    field_name
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }
}

/// Legacy compatibility wrapper for coerce_object_to_array.
pub fn coerce_object_to_array(
    node: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    for field in FORCED_ARRAY_FIELDS {
        coerce_field_if_mapping(node, field, telemetry, changes);
    }
}

/// Lifts misnested container fields out of envFrom items and restructures malformed refs.
pub fn lift_envfrom_misnested_fields(
    container: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let container_indent = container.indent;
    let mut lifted_nodes = Vec::new();

    if let Some(env_from) = container.find_node_mut("envFrom") {
        // 1a. Lift direct misnested fields under envFrom (e.g. envFrom: ports: - containerPort: 80)
        let mut direct_indices_to_remove = Vec::new();
        for (idx, field) in env_from.children.iter().enumerate() {
            if MISNESTED_CONTAINER_KEYS.contains(&field.key.as_str()) {
                direct_indices_to_remove.push(idx);
            }
        }

        let mut direct_lifted = Vec::new();
        for idx in direct_indices_to_remove.into_iter().rev() {
            let mut field_node = env_from.children.remove(idx);
            field_node.indent = container_indent + 2;
            let msg = format!(
                "Remediation [STRUCT-001]: Lifted misnested field '{}' out of envFrom to container level.",
                field_node.key
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
            direct_lifted.push(field_node);
        }
        direct_lifted.reverse();
        lifted_nodes.extend(direct_lifted);

        let mut lifted_item_nodes = Vec::new();
        for env_item in &mut env_from.children {
            let mut indices_to_remove = Vec::new();
            for (idx, field) in env_item.children.iter().enumerate() {
                // Only lift if field is misnested inside envFrom item (indent > container_indent + 2)
                if MISNESTED_CONTAINER_KEYS.contains(&field.key.as_str()) && field.indent > container_indent + 2 {
                    indices_to_remove.push(idx);
                }
            }

            for idx in indices_to_remove.into_iter().rev() {
                let mut field_node = env_item.children.remove(idx);
                field_node.indent = container_indent + 2;
                let msg = format!(
                    "Remediation [STRUCT-001]: Lifted misnested field '{}' out of envFrom to container level.",
                    field_node.key
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
                lifted_item_nodes.push(field_node);
            }

            // Reverse lifted_item_nodes to preserve original top-to-bottom document order
            lifted_item_nodes.reverse();
            lifted_nodes.append(&mut lifted_item_nodes);

            // 2. Repair malformed ref structure (sibling 'name' next to empty configMapRef/secretRef)
            let mut sibling_name_val = None;
            let mut sibling_name_idx = None;

            for (idx, field) in env_item.children.iter().enumerate() {
                if field.key == "name" && field.value.is_some() {
                    sibling_name_val = field.value.clone();
                    sibling_name_idx = Some(idx);
                    break;
                }
            }

            if let Some(name_val) = sibling_name_val {
                let mut ref_repaired = false;
                for ref_target in ["configMapRef", "secretRef"] {
                    if let Some(ref_node) = env_item.find_node_mut(ref_target) {
                        if ref_node.find_node("name").is_none() {
                            ref_node.children.push(SemanticNode {
                                key: "name".to_string(),
                                value: Some(name_val.clone()),
                                children: Vec::new(),
                                shards: Vec::new(),
                                indent: ref_node.indent + 2,
                                is_empty_flow: false,
                            });
                            ref_repaired = true;
                            let msg = format!(
                                "Remediation [STRUCT-002]: Restructured misnested 'name: {}' into '{}'.",
                                name_val, ref_target
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                            break;
                        }
                    }
                }

                if ref_repaired {
                    if let Some(idx) = sibling_name_idx {
                        env_item.children.remove(idx);
                    }
                }
            }
        }
    }

    // Push all lifted fields into container root if not already present
    for lifted in lifted_nodes {
        if container.find_node(&lifted.key).is_none() {
            container.children.push(lifted);
        }
    }

    // Clean up empty envFrom node if all fields were lifted
    if let Some(idx) = container.children.iter().position(|c| c.key == "envFrom") {
        if container.children[idx].children.is_empty() {
            container.children.remove(idx);
        }
    }
}

/// Lifts misplaced `volumes:` blocks found inside containers up to pod spec.
pub fn lift_misplaced_volumes(
    pod_spec: &mut SemanticNode,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let mut misplaced_volumes = Vec::new();

    if let Some(containers) = pod_spec.find_node_mut("containers") {
        for container in &mut containers.children {
            if let Some(idx) = container.children.iter().position(|c| c.key == "volumes") {
                let vol_node = container.children.remove(idx);
                let msg = "Remediation [STRUCT-004]: Lifted misplaced 'volumes' block from container to Pod spec level.".to_string();
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
                misplaced_volumes.push(vol_node);
            }
        }
    }

    for vol in misplaced_volumes {
        if let Some(existing_vols) = pod_spec.find_node_mut("volumes") {
            existing_vols.children.extend(vol.children);
        } else {
            pod_spec.children.push(vol);
        }
    }
}

/// Primary Entrypoint: Resolves all structural misnesting and mapping errors.
pub fn heal_structural_issues(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    // 1. Meta-Schema Invariant:
    // CustomResourceDefinitions contain OpenAPI v3 schema definitions, not runtime workloads.
    // Structural coercion and workload lifters must NEVER mutate CRD schemas.
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    // 2. Data Boundary Invariant:
    // ConfigMap and Secret data blocks are opaque user payloads.
    if kind == "ConfigMap" || kind == "Secret" {
        return changes;
    }

    // 3. Pod spec and container structural repairs
    let pod_specs = find_pod_specs_mut(&mut manifest.root);
    for pod_spec in pod_specs {
        // Coerce PodSpec-level array fields
        for field in [
            "containers",
            "initContainers",
            "ephemeralContainers",
            "volumes",
            "imagePullSecrets",
        ] {
            coerce_field_if_mapping(pod_spec, field, telemetry, &mut changes);
        }

        // Misplaced volumes inside container
        lift_misplaced_volumes(pod_spec, telemetry, &mut changes);

        // EnvFrom misnested container properties and container-level array coercion
        if let Some(containers) = pod_spec.find_node_mut("containers") {
            for container in &mut containers.children {
                for field in ["volumeMounts", "ports", "env"] {
                    coerce_field_if_mapping(container, field, telemetry, &mut changes);
                }
                lift_envfrom_misnested_fields(container, telemetry, &mut changes);
            }
        }

        if let Some(init_containers) = pod_spec.find_node_mut("initContainers") {
            for init_container in &mut init_containers.children {
                for field in ["volumeMounts", "ports", "env"] {
                    coerce_field_if_mapping(init_container, field, telemetry, &mut changes);
                }
                lift_envfrom_misnested_fields(init_container, telemetry, &mut changes);
            }
        }
    }

    // 4. Role / ClusterRole rules coercion
    if kind == "Role" || kind == "ClusterRole" {
        coerce_field_if_mapping(&mut manifest.root, "rules", telemetry, &mut changes);
    }

    // 5. Ingress & Service networking coercion
    if kind == "Ingress" {
        if let Some(spec) = manifest.root.find_node_mut("spec") {
            coerce_field_if_mapping(spec, "rules", telemetry, &mut changes);
            coerce_field_if_mapping(spec, "tls", telemetry, &mut changes);
        }
    } else if kind == "Service" {
        if let Some(spec) = manifest.root.find_node_mut("spec") {
            coerce_field_if_mapping(spec, "ports", telemetry, &mut changes);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lift_misnested_ports_from_envfrom() {
        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();

        let mut container = SemanticNode {
            key: "-".to_string(),
            value: None,
            indent: 4,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![
                SemanticNode {
                    key: "name".to_string(),
                    value: Some("app".to_string()),
                    indent: 6,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                },
                SemanticNode {
                    key: "envFrom".to_string(),
                    value: None,
                    indent: 6,
                    is_empty_flow: false,
                    shards: Vec::new(),
                    children: vec![SemanticNode {
                        key: "-".to_string(),
                        value: None,
                        indent: 8,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "ports".to_string(),
                            value: None,
                            indent: 10,
                            is_empty_flow: false,
                            children: vec![SemanticNode {
                                key: "-".to_string(),
                                value: None,
                                indent: 12,
                                is_empty_flow: false,
                                children: vec![SemanticNode {
                                    key: "containerPort".to_string(),
                                    value: Some("80".to_string()),
                                    indent: 14,
                                    is_empty_flow: false,
                                    children: Vec::new(),
                                    shards: Vec::new(),
                                }],
                                shards: Vec::new(),
                            }],
                            shards: Vec::new(),
                        }],
                    }],
                },
            ],
        };

        lift_envfrom_misnested_fields(&mut container, &mut telemetry, &mut changes);

        assert!(
            container.find_node("ports").is_some(),
            "Ports should be lifted to container level"
        );
        let env_from = container.find_node("envFrom").unwrap();
        let env_item = &env_from.children[0];
        assert!(
            env_item.find_node("ports").is_none(),
            "Ports should no longer be in envFrom item"
        );
        assert_eq!(changes.len(), 1);
    }

    #[test]
    fn test_crd_immune_to_structural_coercion() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "kind".to_string(),
                        value: Some("CustomResourceDefinition".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: Vec::new(),
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "imagePullSecrets".to_string(),
                            value: None,
                            indent: 2,
                            is_empty_flow: false,
                            shards: Vec::new(),
                            children: vec![SemanticNode {
                                key: "type".to_string(),
                                value: Some("array".to_string()),
                                indent: 4,
                                is_empty_flow: false,
                                shards: Vec::new(),
                                children: Vec::new(),
                            }],
                        }],
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_structural_issues(&mut manifest, &mut telemetry);
        assert!(changes.is_empty(), "CRD must not be mutated by structural healers");
        let spec = manifest.root.find_node("spec").unwrap();
        let ips = spec.find_node("imagePullSecrets").unwrap();
        assert!(ips.find_node("-").is_none(), "imagePullSecrets in CRD schema must not be coerced to array");
    }
}
