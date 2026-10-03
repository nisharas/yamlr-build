//! 7-Tier GitOps Sync-Wave & Phase Ordering Stamping Engine.
//!
//! Why: In GitOps pipelines (ArgoCD, Flux, Helm), manifests deployed without
//! deterministic phase ordering trigger race conditions (e.g. CRD missing before CR,
//! ConfigMap missing before Pod startup, Ingress resolving before Service).

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const RULE_GITOPS_WAVE: &str = "GTO-003";

/// Determines the enterprise 7-tier GitOps wave ordering for any Kubernetes resource.
pub fn calculate_enterprise_gitops_wave(kind: &str, name: &str) -> i32 {
    let lower_name = name.to_lowercase();
    if (kind == "Job" || kind == "Pod")
        && (lower_name.contains("cleanup") || lower_name.contains("prune"))
    {
        return 5;
    }

    match kind {
        // Tier -5: Namespaces, CRDs
        "Namespace" | "CustomResourceDefinition" => -5,

        // Tier -3: ConfigMaps, Secrets, ServiceAccounts, RBAC
        "ConfigMap" | "Secret" | "ServiceAccount" | "ClusterRole" | "ClusterRoleBinding"
        | "Role" | "RoleBinding" => -3,

        // Tier -2: PVCs, Storage
        "PersistentVolume"
        | "PersistentVolumeClaim"
        | "StorageClass"
        | "VolumeSnapshot"
        | "VolumeSnapshotClass" => -2,

        // Tier 0: Core Workloads
        "Deployment" | "StatefulSet" | "DaemonSet" | "Pod" | "ReplicaSet" | "Rollout" => 0,

        // Tier 2: Ingress, Gateways, Routes
        "Ingress" | "Gateway" | "HTTPRoute" | "GRPCRoute" | "TCPRoute" | "TLSRoute" | "Service" => {
            2
        }

        // Tier 3: Autoscalers, PDBs, NetworkPolicies
        "HorizontalPodAutoscaler"
        | "PodDisruptionBudget"
        | "NetworkPolicy"
        | "CiliumNetworkPolicy" => 3,

        // Tier 5: Batch Jobs, Cleanup
        "Job" | "CronJob" => 5,

        _ => 0,
    }
}

/// Stamps enterprise GitOps sync-wave and hook-weight annotations across manifests.
pub fn native_stamp_gitops_waves(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind.is_empty() {
        return changes;
    }

    let resource_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_default();

    let target_wave = calculate_enterprise_gitops_wave(&kind, &resource_name);
    let wave_str = format!("\"{}\"", target_wave);

    // 1. Stamp ArgoCD sync-wave
    let mut stamped_argo = false;
    if manifest
        .root
        .find_annotation("argocd.argoproj.io/sync-wave")
        .is_none()
    {
        if set_annotation(
            &mut manifest.root,
            "argocd.argoproj.io/sync-wave",
            &wave_str,
        ) {
            let msg = format!(
                "Remediation [{}]: Stamped ArgoCD wave 'argocd.argoproj.io/sync-wave: \"{}\"' on {} '{}'.",
                RULE_GITOPS_WAVE, target_wave, kind, resource_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
            stamped_argo = true;
        }
    }

    // 2. Stamp Helm hook-weight
    if manifest
        .root
        .find_annotation("helm.sh/hook-weight")
        .is_none()
    {
        if set_annotation(&mut manifest.root, "helm.sh/hook-weight", &wave_str) {
            let msg = format!(
                "Remediation [{}]: Stamped Helm hook-weight 'helm.sh/hook-weight: \"{}\"' on {} '{}'.",
                RULE_GITOPS_WAVE, target_wave, kind, resource_name
            );
            native_record_healing_impact(telemetry, &msg);
            changes.push(msg);
        }
    }

    let _ = stamped_argo;
    changes
}

fn set_annotation(root: &mut SemanticNode, key: &str, value: &str) -> bool {
    let meta_indent = 2;
    let ann_indent = 4;
    let item_indent = 6;

    if root.find_node("metadata").is_none() {
        root.children.push(SemanticNode {
            key: "metadata".to_string(),
            value: None,
            indent: meta_indent,
            is_empty_flow: false,
            shards: Vec::new(),
            children: Vec::new(),
        });
    }

    let meta = match root.find_node_mut("metadata") {
        Some(m) => m,
        None => return false,
    };

    if meta.find_node("annotations").is_none() {
        meta.children.push(SemanticNode {
            key: "annotations".to_string(),
            value: None,
            indent: ann_indent,
            is_empty_flow: false,
            shards: Vec::new(),
            children: Vec::new(),
        });
    }

    let annotations = match meta.find_node_mut("annotations") {
        Some(a) => a,
        None => return false,
    };

    if let Some(existing) = annotations.find_node_mut(key) {
        existing.value = Some(value.to_string());
    } else {
        annotations.children.push(SemanticNode {
            key: key.to_string(),
            value: Some(value.to_string()),
            indent: item_indent,
            is_empty_flow: false,
            shards: Vec::new(),
            children: Vec::new(),
        });
    }

    true
}

/// Hardens YAML manifest content string with GitOps annotations directly.
pub fn stamp_gitops_waves_yaml(content: &str) -> (String, Vec<String>) {
    let shards = crate::sharder::native_shard(content);
    let mut manifest = crate::structurer::native_structurize(shards);
    let mut telemetry = NativeTelemetry::default();
    let changes = native_stamp_gitops_waves(&mut manifest, &mut telemetry);
    let reconstructed = crate::healing::native_reconstruct_from_semantic(&manifest);
    (reconstructed, changes)
}
