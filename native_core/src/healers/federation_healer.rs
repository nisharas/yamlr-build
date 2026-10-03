//! Multi-Cluster & Federation Manifest Auto-Healer (Rule ECO-006).
//!
//! Why: Multi-cluster federation frameworks (KubeFed `types.kubefed.io/v1beta1`,
//! SIG Multi-Cluster `multicluster.x-k8s.io/v1alpha1` ServiceExport/ServiceImport)
//! require synchronized placement clusters and overrides. Orphaned cluster overrides
//! or unassigned placements cause silent synchronization stalls across federated clusters.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const FEDERATION_RULE_ID: &str = "ECO-006";

/// Primary entrypoint: Heals multi-cluster federation resources.
pub fn heal_federation_manifests(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();

    if api_version.starts_with("types.kubefed.io") || api_version.starts_with("core.kubefed.io") {
        changes.extend(heal_kubefed_resource(manifest, telemetry));
    } else if api_version.starts_with("multicluster.x-k8s.io") {
        changes.extend(heal_sig_multicluster(manifest, telemetry));
    }

    changes
}

fn heal_kubefed_resource(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let spec = match manifest.root.find_node_mut("spec") {
        Some(s) => s,
        None => return changes,
    };

    // 1. Validate placement.clusters
    let mut placement_clusters = Vec::new();
    if let Some(placement) = spec.find_node_mut("placement") {
        if let Some(clusters_node) = placement.find_node("clusters") {
            for c in &clusters_node.children {
                if let Some(name_node) = c.find_node("name") {
                    if let Some(ref val) = name_node.value {
                        placement_clusters.push(
                            val.trim()
                                .trim_matches(|ch| ch == '\'' || ch == '"')
                                .to_string(),
                        );
                    }
                }
            }
        }

        // If placement block exists but clusters is empty, inject wildcard cluster selector
        if placement_clusters.is_empty() && placement.find_node("clusterSelector").is_none() {
            let indent = placement.indent + 2;
            placement.children.push(SemanticNode {
                key: "clusterSelector".to_string(),
                value: None,
                children: vec![SemanticNode {
                    key: "matchLabels".to_string(),
                    value: None,
                    children: vec![],
                    shards: Vec::new(),
                    indent: indent + 2,
                    is_empty_flow: false,
                }],
                shards: Vec::new(),
                indent,
                is_empty_flow: false,
            });
            let msg = format!(
                "Remediation [{}]: Injected default empty 'clusterSelector: {{}}' for unassigned KubeFed placement.",
                FEDERATION_RULE_ID
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    // 2. Validate overrides: ensure overrides don't target non-existent clusters if placement is explicit
    if !placement_clusters.is_empty() {
        if let Some(overrides_node) = spec.find_node_mut("overrides") {
            for override_item in &mut overrides_node.children {
                if let Some(cluster_name_node) = override_item.find_node_mut("clusterName") {
                    let mut needs_fix = None;
                    if let Some(ref val) = cluster_name_node.value {
                        let clean = val.trim().trim_matches(|ch| ch == '\'' || ch == '"');
                        if !placement_clusters.contains(&clean.to_string()) {
                            let target = placement_clusters[0].clone();
                            needs_fix = Some((clean.to_string(), target));
                        }
                    }
                    if let Some((clean, target)) = needs_fix {
                        cluster_name_node.value = Some(target.clone());
                        for s in &mut cluster_name_node.shards {
                            s.value = Some(target.clone());
                        }
                        let msg = format!(
                            "Remediation [{}]: Realigned orphaned override clusterName '{}' -> '{}' to match placement.",
                            FEDERATION_RULE_ID, clean, target
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    }

    changes
}

fn heal_sig_multicluster(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();

    if kind == "ServiceExport" {
        // Ensure namespace is not empty (must be explicitly namespaced)
        if let Some(meta) = manifest.root.find_node_mut("metadata") {
            if meta.find_node("namespace").is_none() {
                let indent = meta.indent + 2;
                meta.children.push(SemanticNode {
                    key: "namespace".to_string(),
                    value: Some("default".to_string()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent,
                    is_empty_flow: false,
                });
                let msg = format!(
                    "Remediation [{}]: Injected required 'namespace: default' for SIG MultiCluster ServiceExport.",
                    FEDERATION_RULE_ID
                );
                native_record_healing_impact(telemetry, &msg);
                changes.push(msg);
            }
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sharder::native_shard;
    use crate::structurer::native_structurize;

    #[test]
    fn test_heal_kubefed_empty_placement_cluster_selector() {
        let yaml = r#"
apiVersion: types.kubefed.io/v1beta1
kind: FederatedDeployment
metadata:
  name: test-deploy
spec:
  placement: {}
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_federation_manifests(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("clusterSelector"));
    }

    #[test]
    fn test_heal_sig_multicluster_service_export_namespace() {
        let yaml = r#"
apiVersion: multicluster.x-k8s.io/v1alpha1
kind: ServiceExport
metadata:
  name: my-svc
"#;
        let mut manifest = native_structurize(native_shard(yaml));
        let mut telemetry = NativeTelemetry::default();
        let changes = heal_federation_manifests(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 1);
        assert_eq!(
            manifest
                .root
                .find_node("metadata")
                .unwrap()
                .find_value("namespace"),
            Some("default".to_string())
        );
    }
}
