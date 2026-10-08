//! Schema Property Key Typo Correction Engine (Feature 1 of 15).
//!
//! Uses scoped Levenshtein edit-distance matching against official Kubernetes
//! OpenAPI property dictionaries to auto-correct drifted or misspelled YAML keys.
//!
//! Examples:
//! - `continers:` -> `containers:`
//! - `replica:` -> `replicas:`
//! - `label:` / `laels:` -> `labels:`
//! - `selectr:` -> `selector:`
//! - `apiversion:` -> `apiVersion:`

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub static ROOT_KEYS: &[&str] = &[
    "apiVersion",
    "kind",
    "metadata",
    "spec",
    "status",
    "data",
    "stringData",
    "type",
];

pub static METADATA_KEYS: &[&str] = &[
    "name",
    "namespace",
    "labels",
    "annotations",
    "generation",
    "uid",
    "resourceVersion",
    "creationTimestamp",
    "deletionTimestamp",
    "ownerReferences",
    "finalizers",
];

pub static WORKLOAD_SPEC_KEYS: &[&str] = &[
    "replicas",
    "selector",
    "template",
    "strategy",
    "minReadySeconds",
    "revisionHistoryLimit",
    "paused",
    "progressDeadlineSeconds",
];

pub static POD_SPEC_KEYS: &[&str] = &[
    "containers",
    "initContainers",
    "ephemeralContainers",
    "volumes",
    "restartPolicy",
    "terminationGracePeriodSeconds",
    "dnsPolicy",
    "nodeSelector",
    "serviceAccountName",
    "serviceAccount",
    "hostNetwork",
    "hostPID",
    "hostIPC",
    "securityContext",
    "imagePullSecrets",
    "affinity",
    "tolerations",
    "priorityClassName",
    "automountServiceAccountToken",
    "schedulerName",
];

pub static CONTAINER_KEYS: &[&str] = &[
    "name",
    "image",
    "command",
    "args",
    "workingDir",
    "ports",
    "env",
    "envFrom",
    "resources",
    "volumeMounts",
    "volumeDevices",
    "livenessProbe",
    "readinessProbe",
    "startupProbe",
    "lifecycle",
    "terminationMessagePath",
    "terminationMessagePolicy",
    "imagePullPolicy",
    "securityContext",
    "stdin",
    "stdinOnce",
    "tty",
];

pub static SERVICE_SPEC_KEYS: &[&str] = &[
    "ports",
    "selector",
    "type",
    "clusterIP",
    "clusterIPs",
    "externalIPs",
    "sessionAffinity",
    "loadBalancerIP",
    "loadBalancerSourceRanges",
    "externalName",
    "externalTrafficPolicy",
    "ipFamilies",
    "ipFamilyPolicy",
];

pub static SERVICE_REFERENCE_KEYS: &[&str] = &[
    "name",
    "namespace",
    "path",
    "port",
];

pub static SERVICE_PORT_KEYS: &[&str] = &[
    "name",
    "protocol",
    "port",
    "targetPort",
    "nodePort",
    "appProtocol",
];

pub static INGRESS_SPEC_KEYS: &[&str] = &["rules", "tls", "ingressClassName", "defaultBackend"];

pub static HTTP_GET_KEYS: &[&str] = &[
    "path",
    "port",
    "host",
    "scheme",
    "httpHeaders",
];

pub static TCP_SOCKET_KEYS: &[&str] = &[
    "port",
    "host",
];

pub static PROBE_KEYS: &[&str] = &[
    "httpGet",
    "tcpSocket",
    "exec",
    "grpc",
    "initialDelaySeconds",
    "timeoutSeconds",
    "periodSeconds",
    "successThreshold",
    "failureThreshold",
    "terminationGracePeriodSeconds",
];

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

    // Select candidate properties based on current AST hierarchy
    let candidates: Option<&[&str]> = if path.is_empty() {
        Some(ROOT_KEYS)
    } else if parent_path == "metadata" || parent_path.ends_with(".metadata") {
        Some(METADATA_KEYS)
    } else if parent_path == "spec" {
        if kind == "Service" {
            Some(SERVICE_SPEC_KEYS)
        } else if kind == "Ingress" {
            Some(INGRESS_SPEC_KEYS)
        } else {
            Some(WORKLOAD_SPEC_KEYS)
        }
    } else if parent_path == "spec.template.spec" || parent_path == "template.spec" {
        Some(POD_SPEC_KEYS)
    } else if parent_path.ends_with(".httpGet") || parent_path == "httpGet" {
        Some(HTTP_GET_KEYS)
    } else if parent_path.ends_with(".tcpSocket") || parent_path == "tcpSocket" {
        Some(TCP_SOCKET_KEYS)
    } else if parent_path.ends_with(".livenessProbe")
        || parent_path.ends_with(".readinessProbe")
        || parent_path.ends_with(".startupProbe")
    {
        Some(PROBE_KEYS)
    } else if parent_path.ends_with(".service") || parent_path == "service" {
        Some(SERVICE_REFERENCE_KEYS)
    } else if parent_path.ends_with(".ports") || parent_path == "ports" || parent_path.contains("spec.ports") {
        Some(SERVICE_PORT_KEYS)
    } else if parent_path.ends_with("containers")
        || parent_path.ends_with("containers.-")
        || parent_path.ends_with("initContainers")
        || parent_path.ends_with("initContainers.-")
        || parent_path.ends_with("ephemeralContainers")
        || parent_path.ends_with("ephemeralContainers.-")
    {
        Some(CONTAINER_KEYS)
    } else if parent_path.contains("ingress") {
        Some(INGRESS_SPEC_KEYS)
    } else {
        None
    };

    // Check and repair typos on child keys
    for child in &mut node.children {
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

    // Check root-level keys
    heal_node_recursive(&mut manifest.root, &mut path, &kind, telemetry, &mut changes);

    changes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_levenshtein_distance() {
        assert_eq!(levenshtein("continers", "containers"), 1);
        assert_eq!(levenshtein("replica", "replicas"), 1);
        assert_eq!(levenshtein("laels", "labels"), 1);
        assert_eq!(levenshtein("label", "labels"), 1);
        assert_eq!(levenshtein("selectr", "selector"), 1);
    }

    #[test]
    fn test_fuzzy_match_property() {
        assert_eq!(
            fuzzy_match_property("continers", POD_SPEC_KEYS),
            Some("containers")
        );
        assert_eq!(
            fuzzy_match_property("containrs", POD_SPEC_KEYS),
            Some("containers")
        );
        assert_eq!(
            fuzzy_match_property("replica", WORKLOAD_SPEC_KEYS),
            Some("replicas")
        );
        assert_eq!(fuzzy_match_property("label", METADATA_KEYS), Some("labels"));
        assert_eq!(fuzzy_match_property("laels", METADATA_KEYS), Some("labels"));
        assert_eq!(
            fuzzy_match_property("selectr", WORKLOAD_SPEC_KEYS),
            Some("selector")
        );
    }

    #[test]
    fn test_short_keys_ignored() {
        // Short keys (< 4 characters) like 'app', 'env', 'dev' must not be auto-corrected
        assert_eq!(fuzzy_match_property("app", ROOT_KEYS), None);
        assert_eq!(fuzzy_match_property("env", CONTAINER_KEYS), None);
    }

    #[test]
    fn test_case_insensitive_match() {
        assert_eq!(
            fuzzy_match_property("apiversion", ROOT_KEYS),
            Some("apiVersion")
        );
        assert_eq!(
            fuzzy_match_property("securitycontext", CONTAINER_KEYS),
            Some("securityContext")
        );
    }

    #[test]
    fn test_service_reference_port_preserved() {
        // 'port' under a service reference (webhook clientConfig.service or ingress backend)
        // is valid singular integer property and MUST NOT be converted to 'ports'.
        assert_eq!(fuzzy_match_property("port", SERVICE_REFERENCE_KEYS), None);
        // But typos in 'port' like 'prt' or 'portt' should heal to 'port'
        assert_eq!(fuzzy_match_property("portt", SERVICE_REFERENCE_KEYS), Some("port"));
        assert_eq!(fuzzy_match_property("name", SERVICE_REFERENCE_KEYS), None);
        assert_eq!(fuzzy_match_property("namme", SERVICE_REFERENCE_KEYS), Some("name"));
    }

    #[test]
    fn test_service_port_keys_preserved() {
        // Under spec.ports, 'port' is valid singular and 'targetPort' is valid camelCase
        assert_eq!(fuzzy_match_property("port", SERVICE_PORT_KEYS), None);
        assert_eq!(fuzzy_match_property("targetPort", SERVICE_PORT_KEYS), None);
        assert_eq!(fuzzy_match_property("targetport", SERVICE_PORT_KEYS), Some("targetPort"));
        assert_eq!(fuzzy_match_property("nodeport", SERVICE_PORT_KEYS), Some("nodePort"));
    }

    #[test]
    fn test_probe_httpget_port_preserved() {
        // Under httpGet, 'port' is valid singular and MUST NOT be converted to 'ports'.
        assert_eq!(fuzzy_match_property("port", HTTP_GET_KEYS), None);
        assert_eq!(fuzzy_match_property("portt", HTTP_GET_KEYS), Some("port"));
        assert_eq!(fuzzy_match_property("path", HTTP_GET_KEYS), None);
    }
}
