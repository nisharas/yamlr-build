//! Schema Property Key Typo Correction Engine (Feature 1 of 15).
//!
//! Uses scoped Levenshtein edit-distance matching against official Kubernetes
//! OpenAPI property dictionaries to auto-correct drifted or misspelled YAML keys.
//!
//! Dictionaries and contextual scopes are isolated in `typo_dictionaries.rs` to prevent
//! keyword collision traps across singular/plural and resource-specific properties.
//!
//! Examples:
//! - `continers:` -> `containers:`
//! - `replica:` -> `replicas:`
//! - `label:` / `laels:` -> `labels:`
//! - `selectr:` -> `selector:`
//! - `apiversion:` -> `apiVersion:`

pub use super::typo_dictionaries::*;
use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

/// Calculates standard Levenshtein edit distance between two UTF-8 strings.
pub fn levenshtein(a: &str, b: &str) -> usize {
    let a_bytes = a.as_bytes();
    let b_bytes = b.as_bytes();
    let mut dp: Vec<usize> = (0..=b_bytes.len()).collect();

    for (i, &ca) in a_bytes.iter().enumerate() {
        let mut prev = dp[0];
        dp[0] = i + 1;
        for (j, &cb) in b_bytes.iter().enumerate() {
            let temp = dp[j + 1];
            if ca == cb {
                dp[j + 1] = prev;
            } else {
                dp[j + 1] = 1 + prev.min(dp[j]).min(dp[j + 1]);
            }
            prev = temp;
        }
    }
    dp[b_bytes.len()]
}

/// Matches an input key against a list of candidate schema properties.
/// Returns the corrected property name if an exact case-mismatch or edit-distance typo <= 2 is found.
pub fn fuzzy_match_property<'a>(input: &str, candidate_keys: &'a [&'a str]) -> Option<&'a str> {
    // Guard: Skip short keys (< 4 characters) to protect labels like 'app', 'env', 'dev'
    if input.len() < 4 {
        return None;
    }

    // 1. Exact match already valid
    if candidate_keys.contains(&input) {
        return None;
    }

    let input_lower = input.to_lowercase();

    // 2. Case-insensitive exact match
    for &cand in candidate_keys {
        if cand.to_lowercase() == input_lower {
            return Some(cand);
        }
    }

    // 3. Levenshtein edit distance <= 2
    // Guard: 'appVersion' is a standard Helm Chart.yaml metadata field, distinct from 'apiVersion'
    if input == "appVersion" {
        return None;
    }

    let mut best_match = None;
    let mut min_dist = 3;

    for &cand in candidate_keys {
        let cand_lower = cand.to_lowercase();
        let dist = levenshtein(&input_lower, &cand_lower);

        if dist < min_dist {
            min_dist = dist;
            best_match = Some(cand);
        }
    }

    best_match
}

/// Recursively traverses and heals schema property typos in a SemanticNode tree.
fn heal_node_recursive(
    node: &mut SemanticNode,
    path: &mut Vec<String>,
    kind: &str,
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let parent_path = path.join(".");

    // Guard 1: CustomResourceDefinition OpenAPI schemas are 100% immune to typo coercion
    if kind == "CustomResourceDefinition"
        && (parent_path.starts_with("spec.versions")
            || parent_path.starts_with("spec.validation")
            || parent_path.contains("schema"))
    {
        return;
    }
    if parent_path.contains("openAPIV3Schema") || parent_path.contains("properties.") {
        return;
    }

    // Guard 2: Payload data blocks in ConfigMap and Secret are opaque user payloads
    if parent_path == "data"
        || parent_path.ends_with(".data")
        || parent_path == "stringData"
        || parent_path.ends_with(".stringData")
        || parent_path == "binaryData"
        || parent_path.ends_with(".binaryData")
    {
        return;
    }

    let is_in_container = parent_path.contains("containers")
        || parent_path.contains("initContainers")
        || parent_path.contains("ephemeralContainers");

    // Select candidate properties based on current AST hierarchy
    let candidates: Option<&[&str]> = if path.is_empty() {
        Some(ROOT_KEYS)
    } else if parent_path == "metadata" || parent_path.ends_with(".metadata") {
        Some(METADATA_KEYS)
    } else if parent_path.ends_with(".httpGet") || parent_path == "httpGet" {
        Some(HTTP_GET_KEYS)
    } else if parent_path.ends_with(".tcpSocket") || parent_path == "tcpSocket" {
        Some(TCP_SOCKET_KEYS)
    } else if parent_path.ends_with(".grpc") || parent_path == "grpc" {
        Some(GRPC_PROBE_KEYS)
    } else if parent_path.ends_with(".livenessProbe")
        || parent_path.ends_with(".readinessProbe")
        || parent_path.ends_with(".startupProbe")
    {
        Some(PROBE_KEYS)
    } else if parent_path.ends_with(".backend.service.port")
        || parent_path.ends_with(".service.port")
    {
        Some(INGRESS_SERVICE_PORT_KEYS)
    } else if parent_path.ends_with(".service") || parent_path == "service" {
        Some(SERVICE_REFERENCE_KEYS)
    } else if is_in_container && (parent_path.ends_with(".ports") || parent_path.ends_with(".ports.-")) {
        Some(CONTAINER_PORT_KEYS)
    } else if parent_path.ends_with(".volumeMounts") || parent_path.ends_with(".volumeMounts.-") {
        Some(VOLUME_MOUNT_KEYS)
    } else if parent_path.ends_with(".volumeDevices") || parent_path.ends_with(".volumeDevices.-") {
        Some(VOLUME_DEVICE_KEYS)
    } else if parent_path.ends_with(".volumes") || parent_path.ends_with(".volumes.-") {
        Some(VOLUME_SPEC_KEYS)
    } else if parent_path.ends_with(".secret") {
        Some(VOLUME_SECRET_KEYS)
    } else if parent_path.ends_with(".configMap") {
        Some(VOLUME_CONFIG_MAP_KEYS)
    } else if parent_path.ends_with(".secretKeyRef") || parent_path.ends_with(".configMapKeyRef") {
        Some(KEY_REF_KEYS)
    } else if parent_path.ends_with(".secretRef") || parent_path.ends_with(".configMapRef") {
        Some(OBJECT_REF_KEYS)
    } else if parent_path.ends_with(".valueFrom") {
        Some(VALUE_FROM_KEYS)
    } else if parent_path.ends_with(".resourceFieldRef") {
        Some(RESOURCE_FIELD_REF_KEYS)
    } else if parent_path.ends_with(".fieldRef") {
        Some(OBJECT_FIELD_SELECTOR_KEYS)
    } else if parent_path.ends_with(".env") || parent_path.ends_with(".env.-") || parent_path == "env" {
        Some(ENV_VAR_KEYS)
    } else if parent_path.ends_with(".envFrom") || parent_path.ends_with(".envFrom.-") || parent_path == "envFrom" {
        Some(ENV_FROM_KEYS)
    } else if parent_path.ends_with(".securityContext") || parent_path == "securityContext" {
        Some(SECURITY_CONTEXT_KEYS)
    } else if parent_path.ends_with(".resources") || parent_path == "resources" {
        Some(RESOURCE_KEYS)
    } else if kind == "Service"
        && (parent_path == "spec.ports"
            || parent_path == "spec.ports.-"
            || parent_path.ends_with(".ports")
            || parent_path.ends_with(".ports.-")
            || parent_path == "ports")
    {
        Some(SERVICE_PORT_KEYS)
    } else if kind == "Service" && parent_path == "spec" {
        Some(SERVICE_SPEC_KEYS)
    } else if kind == "Ingress" && parent_path == "spec" {
        Some(INGRESS_SPEC_KEYS)
    } else if kind == "Ingress" && (parent_path.ends_with(".tls") || parent_path.ends_with(".tls.-")) {
        Some(INGRESS_TLS_KEYS)
    } else if kind == "HorizontalPodAutoscaler" && parent_path == "spec" {
        Some(HPA_SPEC_KEYS)
    } else if kind == "HorizontalPodAutoscaler"
        && (parent_path == "spec.metrics" || parent_path == "spec.metrics.-" || parent_path.ends_with(".metrics.-"))
    {
        Some(HPA_METRIC_KEYS)
    } else if kind == "HorizontalPodAutoscaler" && parent_path.ends_with(".resource") {
        Some(HPA_RESOURCE_METRIC_KEYS)
    } else if kind == "HorizontalPodAutoscaler" && parent_path.ends_with(".target") {
        Some(HPA_METRIC_TARGET_KEYS)
    } else if (kind == "Role" || kind == "ClusterRole")
        && (parent_path == "rules" || parent_path.ends_with(".rules") || parent_path.ends_with(".rules.-"))
    {
        Some(RBAC_RULE_KEYS)
    } else if (kind == "RoleBinding" || kind == "ClusterRoleBinding")
        && (parent_path == "roleRef" || parent_path.ends_with(".roleRef"))
    {
        Some(RBAC_ROLE_REF_KEYS)
    } else if (kind == "RoleBinding" || kind == "ClusterRoleBinding")
        && (parent_path == "subjects" || parent_path.ends_with(".subjects") || parent_path.ends_with(".subjects.-"))
    {
        Some(RBAC_SUBJECT_KEYS)
    } else if kind == "NetworkPolicy" && parent_path == "spec" {
        Some(NETWORK_POLICY_SPEC_KEYS)
    } else if kind == "NetworkPolicy"
        && (parent_path.contains("ingress") || parent_path.contains("egress"))
    {
        Some(NETWORK_POLICY_PEER_KEYS)
    } else if parent_path == "spec.selector"
        || parent_path.ends_with(".selector")
        || parent_path.ends_with(".podSelector")
        || parent_path.ends_with(".namespaceSelector")
    {
        if kind == "Service" {
            None
        } else {
            Some(WORKLOAD_SELECTOR_KEYS)
        }
    } else if parent_path == "spec.template" || parent_path == "template" {
        Some(POD_TEMPLATE_KEYS)
    } else if parent_path == "spec.template.spec"
        || parent_path == "template.spec"
        || (kind == "Pod" && parent_path == "spec")
    {
        Some(POD_SPEC_KEYS)
    } else if kind == "Job" && parent_path == "spec" {
        Some(JOB_SPEC_KEYS)
    } else if kind == "CronJob" && parent_path == "spec" {
        Some(CRONJOB_SPEC_KEYS)
    } else if kind == "CustomResourceDefinition" {
        None
    } else if parent_path == "spec" {
        Some(WORKLOAD_SPEC_KEYS)
    } else if kind != "CustomResourceDefinition" && is_in_container {
        Some(CONTAINER_KEYS)
    } else {
        None
    };

    // Check and repair typos on child keys
    for child in &mut node.children {
        // Special Case A: In ContainerPort item, 'port:' or 'ports:' is a common Docker Compose typo for 'containerPort:'
        if is_in_container
            && (parent_path.ends_with(".ports.-") || parent_path.ends_with(".ports"))
            && (child.key == "port" || child.key == "ports")
        {
            let old_key = child.key.clone();
            child.key = "containerPort".to_string();
            for shard in &mut child.shards {
                shard.key = "containerPort".to_string();
            }
            let full_loc = format!("{}.{}", parent_path, old_key);
            let msg = format!(
                "Remediation [SCHEMA-002]: Corrected container port item key '{}' -> 'containerPort' at '{}'.",
                old_key, full_loc
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);

            // Recurse into child nodes
            path.push(child.key.clone());
            heal_node_recursive(child, path, kind, telemetry, changes);
            path.pop();
            continue;
        }

        // Special Case B: In Workload selector, 'labels:' or 'label:' is a common typo for 'matchLabels:'
        if (parent_path == "spec.selector"
            || parent_path.ends_with(".selector")
            || parent_path.ends_with(".podSelector")
            || parent_path.ends_with(".namespaceSelector"))
            && kind != "Service"
            && (child.key == "labels" || child.key == "label")
        {
            let old_key = child.key.clone();
            child.key = "matchLabels".to_string();
            for shard in &mut child.shards {
                shard.key = "matchLabels".to_string();
            }
            let full_loc = format!("{}.{}", parent_path, old_key);
            let msg = format!(
                "Remediation [SCHEMA-002]: Corrected workload selector key '{}' -> 'matchLabels' at '{}'.",
                old_key, full_loc
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);

            // Recurse into child nodes
            path.push(child.key.clone());
            heal_node_recursive(child, path, kind, telemetry, changes);
            path.pop();
            continue;
        }

        if let Some(cand_list) = candidates {
            if let Some(corrected) = fuzzy_match_property(&child.key, cand_list) {
                let old_key = child.key.clone();
                let full_loc = if path.is_empty() {
                    old_key.clone()
                } else {
                    format!("{}.{}", parent_path, old_key)
                };

                // Update node key in-place
                child.key = corrected.to_string();

                // Update any associated shard keys
                for shard in &mut child.shards {
                    shard.key = corrected.to_string();
                }

                let msg = format!(
                    "Remediation [SCHEMA-002]: Corrected schema property typo '{}' -> '{}' at '{}'.",
                    old_key, corrected, full_loc
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }

        // Recurse into child nodes
        path.push(child.key.clone());
        heal_node_recursive(child, path, kind, telemetry, changes);
        path.pop();
    }
}

/// Primary Entrypoint: Corrects all schema property key typos across a manifest.
pub fn heal_schema_typos(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let mut path = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    heal_node_recursive(&mut manifest.root, &mut path, &kind, telemetry, &mut changes);

    changes
}

#[cfg(test)]
#[path = "typo_healer_tests.rs"]
mod tests;
