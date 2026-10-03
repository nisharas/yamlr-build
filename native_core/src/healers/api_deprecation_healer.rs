//! Kubernetes API Deprecation & Migration Healer (Rule PRO-001).
//!
//! Why: Kubernetes removes deprecated API versions across releases (e.g. `extensions/v1beta1`
//! removed in 1.16, `networking.k8s.io/v1beta1` removed in 1.22, `batch/v1beta1` removed in 1.25,
//! `autoscaling/v2beta2` removed in 1.26). Manifests using deprecated APIs fail hard upon cluster upgrade.
//!
//! This module checks the manifest's `apiVersion` and `kind` and upgrades them to the GA/supported API.

use crate::models::{NativeTelemetry, SemanticManifest};
use crate::telemetry::native_record_healing_impact;

pub const API_DEPRECATION_RULE_ID: &str = "PRO-001";

/// Resolves the replacement GA/supported apiVersion for a deprecated apiVersion and kind.
pub fn resolve_deprecated_api(clean_api: &str, kind: &str) -> Option<&'static str> {
    match (clean_api, kind) {
        (
            "extensions/v1beta1" | "apps/v1beta1" | "apps/v1beta2",
            "Deployment" | "DaemonSet" | "StatefulSet" | "ReplicaSet",
        ) => Some("apps/v1"),
        ("extensions/v1beta1" | "networking.k8s.io/v1beta1", "Ingress") => {
            Some("networking.k8s.io/v1")
        }
        ("policy/v1beta1", "PodDisruptionBudget") => Some("policy/v1"),
        ("batch/v1beta1" | "batch/v2alpha1", "CronJob") => Some("batch/v1"),
        ("autoscaling/v2beta1" | "autoscaling/v2beta2", "HorizontalPodAutoscaler") => {
            Some("autoscaling/v2")
        }
        (
            "rbac.authorization.k8s.io/v1beta1",
            "Role" | "ClusterRole" | "RoleBinding" | "ClusterRoleBinding",
        ) => Some("rbac.authorization.k8s.io/v1"),
        ("extensions/v1beta1", "NetworkPolicy") => Some("networking.k8s.io/v1"),
        ("storage.k8s.io/v1beta1", "CSINode" | "StorageClass" | "VolumeAttachment") => {
            Some("storage.k8s.io/v1")
        }
        (
            "admissionregistration.k8s.io/v1beta1",
            "ValidatingWebhookConfiguration" | "MutatingWebhookConfiguration",
        ) => Some("admissionregistration.k8s.io/v1"),
        ("apiextensions.k8s.io/v1beta1", "CustomResourceDefinition") => {
            Some("apiextensions.k8s.io/v1")
        }
        ("certificates.k8s.io/v1beta1", "CertificateSigningRequest") => {
            Some("certificates.k8s.io/v1")
        }
        ("discovery.k8s.io/v1beta1", "EndpointSlice") => Some("discovery.k8s.io/v1"),
        (
            "flowcontrol.apiserver.k8s.io/v1beta1" | "flowcontrol.apiserver.k8s.io/v1beta2",
            "FlowSchema" | "PriorityLevelConfiguration",
        ) => Some("flowcontrol.apiserver.k8s.io/v1"),
        _ => None,
    }
}

/// Upgrades deprecated API versions in-place in the manifest AST.
pub fn heal_api_deprecations(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let api_version = manifest.root.find_value("apiVersion").unwrap_or_default();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    let clean_api = api_version.trim_matches('"').trim_matches('\'').to_string();

    if let Some(new_api) = resolve_deprecated_api(&clean_api, &kind) {
        if clean_api != new_api {
            if let Some(node) = manifest.root.find_node_mut("apiVersion") {
                node.value = Some(new_api.to_string());
                for s in &mut node.shards {
                    s.value = Some(new_api.to_string());
                }
                let msg = format!(
                    "Remediation [{}]: Migrated {} from '{}' to '{}'.",
                    API_DEPRECATION_RULE_ID, kind, clean_api, new_api
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
    use crate::models::{NativeShard, SemanticNode};

    #[test]
    fn test_migrate_deprecated_deployment_api() {
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: "root".into(),
                value: None,
                children: vec![
                    SemanticNode {
                        key: "apiVersion".into(),
                        value: Some("extensions/v1beta1".into()),
                        children: vec![],
                        shards: vec![NativeShard {
                            raw_line: "apiVersion: extensions/v1beta1".into(),
                            key: "apiVersion".into(),
                            value: Some("extensions/v1beta1".into()),
                            ..Default::default()
                        }],
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
                ],
                shards: vec![],
                indent: 0,
                is_empty_flow: false,
            },
            indent_step: 2,
            integrity_violations: vec![],
        };

        let mut telemetry = NativeTelemetry::default();
        let changes = heal_api_deprecations(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert_eq!(manifest.root.find_value("apiVersion").unwrap(), "apps/v1");
        assert_eq!(
            manifest.root.find_node("apiVersion").unwrap().shards[0]
                .value
                .as_deref(),
            Some("apps/v1")
        );
    }

    #[test]
    fn test_migrate_ingress_v1beta1_to_v1() {
        assert_eq!(
            resolve_deprecated_api("networking.k8s.io/v1beta1", "Ingress"),
            Some("networking.k8s.io/v1")
        );
        assert_eq!(
            resolve_deprecated_api("policy/v1beta1", "PodDisruptionBudget"),
            Some("policy/v1")
        );
        assert_eq!(
            resolve_deprecated_api("batch/v1beta1", "CronJob"),
            Some("batch/v1")
        );
    }
}
