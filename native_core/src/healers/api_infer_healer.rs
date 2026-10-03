//! API Version Inference Engine (Feature 9 of 15).
//!
//! Why: Kubernetes manifests lacking `apiVersion:` fail immediately with
//! `error: Object 'Kind' is missing apiVersion`. Developers frequently draft
//! manifests specifying only `kind: Deployment` or `kind: Service`.
//!
//! This module infers the canonical, production-stable Kubernetes `apiVersion`
//! directly from the resource `Kind` and injects it deterministically at root.

use crate::models::{NativeSchema, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

/// Returns canonical production apiVersion for standard Kubernetes kinds.
pub fn infer_api_version_for_kind(kind: &str) -> Option<&'static str> {
    match kind {
        "Pod"
        | "Service"
        | "ConfigMap"
        | "Secret"
        | "PersistentVolumeClaim"
        | "PersistentVolume"
        | "Namespace"
        | "ServiceAccount"
        | "Endpoints"
        | "LimitRange"
        | "ResourceQuota"
        | "Node"
        | "Event" => Some("v1"),

        "Deployment" | "StatefulSet" | "DaemonSet" | "ReplicaSet" => Some("apps/v1"),

        "Job" | "CronJob" => Some("batch/v1"),

        "Ingress" | "NetworkPolicy" | "IngressClass" => Some("networking.k8s.io/v1"),

        "Role" | "RoleBinding" | "ClusterRole" | "ClusterRoleBinding" => {
            Some("rbac.authorization.k8s.io/v1")
        }

        "HorizontalPodAutoscaler" => Some("autoscaling/v2"),

        "CustomResourceDefinition" => Some("apiextensions.k8s.io/v1"),

        "StorageClass" | "VolumeAttachment" | "CSIDriver" | "CSINode" => Some("storage.k8s.io/v1"),

        "PodDisruptionBudget" => Some("policy/v1"),

        "Certificate" | "Issuer" | "ClusterIssuer" => Some("cert-manager.io/v1"),

        "VirtualService" | "Gateway" | "DestinationRule" => Some("networking.istio.io/v1beta1"),

        _ => None,
    }
}

/// Primary Entrypoint: Injects missing apiVersion inferred from Kind.
pub fn heal_missing_api_version(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    heal_missing_api_version_with_schemas(manifest, telemetry, &[])
}

/// Injects the apiVersion declared by the selected target schema, falling back to canonical inference.
pub fn heal_missing_api_version_with_schemas(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
    schemas: &[NativeSchema],
) -> Vec<String> {
    let mut changes = Vec::new();

    let kind = match manifest.root.find_value("kind") {
        Some(k) => k,
        None => return changes,
    };

    let has_api = manifest
        .root
        .find_node("apiVersion")
        .and_then(|n| n.value.as_ref())
        .map(|v| !v.trim().is_empty())
        .unwrap_or(false);

    if !has_api {
        let inferred = schemas
            .iter()
            .find(|schema| schema.kind == kind && !schema.api_version.is_empty())
            .map(|schema| schema.api_version.as_str())
            .or_else(|| infer_api_version_for_kind(&kind));
        if let Some(inferred) = inferred {
            // If empty apiVersion node exists, update it; otherwise insert at top
            if let Some(api_node) = manifest.root.find_node_mut("apiVersion") {
                api_node.value = Some(inferred.to_string());
                for s in &mut api_node.shards {
                    s.value = Some(inferred.to_string());
                }
            } else {
                let new_node = SemanticNode {
                    key: "apiVersion".to_string(),
                    value: Some(inferred.to_string()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: 0,
                    is_empty_flow: false,
                };
                // Insert at the very top (index 0)
                manifest.root.children.insert(0, new_node);
            }

            let msg = format!(
                "Remediation [SCHEMA-004]: Injected missing 'apiVersion: {}' inferred from Kind '{}'.",
                inferred, kind
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

    #[test]
    fn test_infer_api_version() {
        assert_eq!(infer_api_version_for_kind("Deployment"), Some("apps/v1"));
        assert_eq!(infer_api_version_for_kind("Service"), Some("v1"));
        assert_eq!(infer_api_version_for_kind("CronJob"), Some("batch/v1"));
        assert_eq!(
            infer_api_version_for_kind("Ingress"),
            Some("networking.k8s.io/v1")
        );
        assert_eq!(
            infer_api_version_for_kind("RoleBinding"),
            Some("rbac.authorization.k8s.io/v1")
        );
    }

    #[test]
    fn test_inject_missing_api_version() {
        let mut telemetry = NativeTelemetry::default();

        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "kind".to_string(),
                    value: Some("Deployment".to_string()),
                    indent: 0,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                }],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };

        let changes = heal_missing_api_version(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert_eq!(
            manifest.root.find_value("apiVersion"),
            Some("apps/v1".to_string())
        );
    }

    #[test]
    fn test_missing_api_version_uses_the_selected_target_schema() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: "kind".into(),
                    value: Some("Ingress".into()),
                    indent: 0,
                    is_empty_flow: false,
                    children: Vec::new(),
                    shards: Vec::new(),
                }],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        };
        let schemas = vec![NativeSchema {
            kind: "Ingress".into(),
            api_version: "networking.k8s.io/v1beta1".into(),
            properties: Vec::new(),
        }];

        let changes =
            heal_missing_api_version_with_schemas(&mut manifest, &mut telemetry, &schemas);

        assert_eq!(changes.len(), 1);
        assert_eq!(
            manifest.root.find_value("apiVersion"),
            Some("networking.k8s.io/v1beta1".into())
        );
    }
}
