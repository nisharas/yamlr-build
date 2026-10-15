//! GitOps Live Cluster Export Sanitizer (Rule GTO-003 / Trap 43).
//!
//! Why: Engineers and automated CI pipelines frequently dump live cluster state
//! (e.g. `kubectl get deployment my-app -o yaml > deploy.yaml`) and commit it directly
//! into GitOps repositories (ArgoCD / Flux). These manifests contain read-only, server-managed
//! runtime fields (`status:`, `metadata.creationTimestamp: null`, `metadata.resourceVersion:`,
//! `metadata.uid:`, `metadata.managedFields:`).
//!
//! In GitOps and standard `kubectl apply`:
//! 1. `resourceVersion` causes fatal 409 Conflict rejection errors when applying updates.
//! 2. `status:` blocks are ignored or cause perpetual GitOps sync-flapping and diff spam.
//! 3. `managedFields` injects thousands of lines of unreadable server-side apply blobs.
//!
//! This module safely and deterministically purges these read-only server artifacts
//! from declarative YAML manifests with zero semantic guesswork.

use crate::models::{NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const RULE_GTO_003: &str = "GTO-003";

/// Server-generated read-only fields under `metadata` that should never be in declarative Git manifests.
pub static SERVER_READONLY_METADATA_FIELDS: &[&str] = &[
    "resourceVersion",
    "uid",
    "generation",
    "managedFields",
    "selfLink",
];

/// Purges server-only status blocks and metadata artifacts from live-exported manifests.
pub fn heal_live_cluster_export_artifacts(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind == "CustomResourceDefinition" {
        return changes;
    }

    let resource_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_else(|| "unnamed".to_string());

    // 1. Prune top-level `status:` block from declarative manifests
    if let Some(pos) = manifest.root.children.iter().position(|c| c.key == "status") {
        manifest.root.children.remove(pos);
        let msg = format!(
            "Remediation [{}]: Pruned read-only 'status' block from {} '{}' to prevent GitOps diff-flap.",
            RULE_GTO_003, kind, resource_name
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }

    // 2. Prune server-generated read-only fields under `metadata`
    if let Some(meta) = manifest.root.find_node_mut("metadata") {
        // Handle creationTimestamp: null or scalar string timestamp
        if let Some(pos) = meta.children.iter().position(|c| c.key == "creationTimestamp") {
            meta.children.remove(pos);
            let msg = format!(
                "Remediation [{}]: Pruned server-generated 'metadata.creationTimestamp' from {} '{}'.",
                RULE_GTO_003, kind, resource_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }

        // Prune remaining server-generated metadata fields
        let mut pruned_fields = Vec::new();
        meta.children.retain(|c| {
            if SERVER_READONLY_METADATA_FIELDS.contains(&c.key.as_str()) {
                pruned_fields.push(c.key.clone());
                false
            } else {
                true
            }
        });

        for field in pruned_fields {
            let msg = format!(
                "Remediation [{}]: Pruned server-generated 'metadata.{}' from {} '{}' to eliminate 409 Conflict errors.",
                RULE_GTO_003, field, kind, resource_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    changes
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::SemanticNode;

    #[test]
    fn test_prune_live_cluster_export_artifacts() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "apiVersion".into(),
                        value: Some("apps/v1".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "kind".into(),
                        value: Some("Deployment".into()),
                        children: vec![],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "metadata".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "name".into(),
                                value: Some("web-app".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "creationTimestamp".into(),
                                value: Some("null".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "resourceVersion".into(),
                                value: Some("\"987654\"".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            },
                            SemanticNode {
                                key: "uid".into(),
                                value: Some("\"a1b2-c3d4\"".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            },
                        ],
                        shards: vec![],
                        indent: 2,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "spec".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "replicas".into(),
                                value: Some("3".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            },
                        ],
                        shards: vec![],
                        indent: 2,
                        is_empty_flow: false,
                    },
                    SemanticNode {
                        key: "status".into(),
                        value: None,
                        children: vec![
                            SemanticNode {
                                key: "availableReplicas".into(),
                                value: Some("3".into()),
                                children: vec![],
                                shards: vec![],
                                indent: 4,
                                is_empty_flow: false,
                            },
                        ],
                        shards: vec![],
                        indent: 0,
                        is_empty_flow: false,
                    },
                ],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            indent_step: 2,
            integrity_violations: vec![],
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_live_cluster_export_artifacts(&mut manifest, &mut telemetry);

        assert_eq!(changes.len(), 4);
        assert!(manifest.root.find_node("status").is_none());

        let meta = manifest.root.find_node("metadata").unwrap();
        assert!(meta.find_node("creationTimestamp").is_none());
        assert!(meta.find_node("resourceVersion").is_none());
        assert!(meta.find_node("uid").is_none());
        assert_eq!(meta.find_value("name"), Some("web-app".to_string()));
    }
}
