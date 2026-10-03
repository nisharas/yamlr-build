//! GitOps Controller Default Harmonizer & Sync-Wave Stamping (Rules GTO-001 & GTO-002).
//!
//! Why: In GitOps (ArgoCD / Flux), Kubernetes controllers automatically inject default
//! values (e.g., `revisionHistoryLimit: 10`, `progressDeadlineSeconds: 600`, `sessionAffinity: None`)
//! into live cluster state. When omitted in Git manifests, ArgoCD detects a perpetual diff,
//! triggering infinite sync-flapping, burning API server CPU, and breaking automated promotions.
//! Furthermore, deploying CustomResources alongside CustomResourceDefinitions causes fatal
//! "no matches for kind" crashes unless dependency waves are explicitly stamped.
//!
//! This module harmonizes controller defaults and stamps standard GitOps sync waves.

use crate::models::{NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub const GTO_DEFAULTS_RULE_ID: &str = "GTO-001";
pub const GTO_SYNC_WAVE_RULE_ID: &str = "GTO-002";

/// Primary entrypoint: Harmonizes controller defaults and stamps GitOps sync waves.
pub fn heal_gitops_manifest(
    manifest: &mut SemanticManifest,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind.is_empty() {
        return changes;
    }

    // 1. Controller Default Harmonizer (GTO-001)
    let default_changes = harmonize_controller_defaults(manifest, &kind, telemetry);
    changes.extend(default_changes);

    // 2. Autonomous Sync-Wave Stamping (GTO-002)
    let wave_changes = stamp_sync_wave(manifest, &kind, telemetry);
    changes.extend(wave_changes);

    changes
}

/// Injects standard Kubernetes controller defaults into Git manifests to eliminate phantom diffs.
fn harmonize_controller_defaults(
    manifest: &mut SemanticManifest,
    kind: &str,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    match kind {
        "Deployment" => {
            if let Some(spec) = manifest.root.find_node_mut("spec") {
                let spec_indent = spec.indent + 2;

                // spec.revisionHistoryLimit: 10
                if spec.find_node("revisionHistoryLimit").is_none() {
                    spec.children.push(SemanticNode {
                        key: "revisionHistoryLimit".to_string(),
                        value: Some("10".to_string()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent: spec_indent,
                        is_empty_flow: false,
                    });
                    let msg = format!(
                        "Remediation [{}]: Harmonized controller default 'revisionHistoryLimit: 10' on Deployment to eliminate GitOps diff-flap.",
                        GTO_DEFAULTS_RULE_ID
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }

                // spec.progressDeadlineSeconds: 600
                if spec.find_node("progressDeadlineSeconds").is_none() {
                    spec.children.push(SemanticNode {
                        key: "progressDeadlineSeconds".to_string(),
                        value: Some("600".to_string()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent: spec_indent,
                        is_empty_flow: false,
                    });
                    let msg = format!(
                        "Remediation [{}]: Harmonized controller default 'progressDeadlineSeconds: 600' on Deployment to eliminate GitOps diff-flap.",
                        GTO_DEFAULTS_RULE_ID
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
        "StatefulSet" => {
            if let Some(spec) = manifest.root.find_node_mut("spec") {
                let spec_indent = spec.indent + 2;
                if spec.find_node("revisionHistoryLimit").is_none() {
                    spec.children.push(SemanticNode {
                        key: "revisionHistoryLimit".to_string(),
                        value: Some("10".to_string()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent: spec_indent,
                        is_empty_flow: false,
                    });
                    let msg = format!(
                        "Remediation [{}]: Harmonized controller default 'revisionHistoryLimit: 10' on StatefulSet to eliminate GitOps diff-flap.",
                        GTO_DEFAULTS_RULE_ID
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
        "Service" => {
            if let Some(spec) = manifest.root.find_node_mut("spec") {
                let spec_indent = spec.indent + 2;
                if spec.find_node("sessionAffinity").is_none() {
                    spec.children.push(SemanticNode {
                        key: "sessionAffinity".to_string(),
                        value: Some("None".to_string()),
                        children: Vec::new(),
                        shards: Vec::new(),
                        indent: spec_indent,
                        is_empty_flow: false,
                    });
                    let msg = format!(
                        "Remediation [{}]: Harmonized controller default 'sessionAffinity: None' on Service to eliminate GitOps diff-flap.",
                        GTO_DEFAULTS_RULE_ID
                    );
                    native_record_healing_impact(telemetry, &msg);
                    changes.push(msg);
                }
            }
        }
        _ => {}
    }

    changes
}

/// Detects the resource dependency tier and stamps standard GitOps sync-waves.
fn stamp_sync_wave(
    manifest: &mut SemanticManifest,
    kind: &str,
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    // Check if sync-wave annotation is already present
    if let Some(existing_wave) = manifest
        .root
        .find_annotation("argocd.argoproj.io/sync-wave")
    {
        if !existing_wave.trim().is_empty() {
            return changes; // Preserve explicit user configuration
        }
    }

    let resource_name = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("name"))
        .unwrap_or_default()
        .to_lowercase();

    let target_wave = calculate_sync_wave(kind, &resource_name, &manifest.root);

    // Inject annotation
    if set_annotation(
        &mut manifest.root,
        "argocd.argoproj.io/sync-wave",
        &format!("\"{}\"", target_wave),
    ) {
        let msg = format!(
            "Remediation [{}]: Stamped GitOps dependency wave 'argocd.argoproj.io/sync-wave: \"{}\"' on {} '{}'.",
            GTO_SYNC_WAVE_RULE_ID, target_wave, kind, resource_name
        );
        native_record_healing_impact(telemetry, &msg);
        changes.push(msg);
    }

    changes
}

/// Determines the proper sync-wave based on resource kind and purpose.
fn calculate_sync_wave(kind: &str, name: &str, root: &SemanticNode) -> i32 {
    // Tier 1: Verification & Test Jobs
    if kind == "Job" || kind == "Pod" {
        if name.contains("test") || name.contains("verify") || name.contains("check") {
            return 1;
        }
        if let Some(hook) = root.find_annotation("helm.sh/hook") {
            if hook.contains("test") {
                return 1;
            }
        }
    }

    match kind {
        // Tier -2: CRDs, Namespaces, Cluster-level RBAC (Foundation)
        "CustomResourceDefinition" | "Namespace" | "ClusterRole" | "ClusterRoleBinding" => -2,

        // Tier -1: Dependencies, Storage, and Configuration
        "Secret"
        | "ConfigMap"
        | "ServiceAccount"
        | "StorageClass"
        | "PersistentVolume"
        | "PersistentVolumeClaim"
        | "ResourceQuota"
        | "LimitRange" => -1,

        // Tier 0: Standard Workloads, Networking, Routing
        _ => 0,
    }
}

/// Safely sets or creates an annotation on the root node preserving metadata structure.
fn set_annotation(root: &mut SemanticNode, key: &str, value: &str) -> bool {
    if let Some(metadata) = root.find_node_mut("metadata") {
        let meta_indent = metadata.indent + 2;
        if let Some(annotations) = metadata.find_node_mut("annotations") {
            let ann_indent = annotations.indent + 2;
            if let Some(ann) = annotations.find_node_mut(key) {
                ann.value = Some(value.to_string());
                for s in &mut ann.shards {
                    s.value = Some(value.to_string());
                }
            } else {
                annotations.children.push(SemanticNode {
                    key: key.to_string(),
                    value: Some(value.to_string()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: ann_indent,
                    is_empty_flow: false,
                });
            }
            true
        } else {
            metadata.children.push(SemanticNode {
                key: "annotations".to_string(),
                value: None,
                indent: meta_indent,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: key.to_string(),
                    value: Some(value.to_string()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: meta_indent + 2,
                    is_empty_flow: false,
                }],
            });
            true
        }
    } else {
        root.children.push(SemanticNode {
            key: "metadata".to_string(),
            value: None,
            indent: 0,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "annotations".to_string(),
                value: None,
                indent: 2,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![SemanticNode {
                    key: key.to_string(),
                    value: Some(value.to_string()),
                    children: Vec::new(),
                    shards: Vec::new(),
                    indent: 4,
                    is_empty_flow: false,
                }],
            }],
        });
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_manifest(
        kind: &str,
        name: &str,
        spec_children: Vec<SemanticNode>,
    ) -> SemanticManifest {
        SemanticManifest {
            root: SemanticNode {
                key: String::new(),
                value: None,
                indent: 0,
                is_empty_flow: false,
                shards: Vec::new(),
                children: vec![
                    SemanticNode {
                        key: "apiVersion".to_string(),
                        value: Some("apps/v1".to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "kind".to_string(),
                        value: Some(kind.to_string()),
                        indent: 0,
                        is_empty_flow: false,
                        children: vec![],
                        shards: vec![],
                    },
                    SemanticNode {
                        key: "metadata".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: vec![SemanticNode {
                            key: "name".to_string(),
                            value: Some(name.to_string()),
                            indent: 2,
                            is_empty_flow: false,
                            children: vec![],
                            shards: vec![],
                        }],
                    },
                    SemanticNode {
                        key: "spec".to_string(),
                        value: None,
                        indent: 0,
                        is_empty_flow: false,
                        shards: Vec::new(),
                        children: spec_children,
                    },
                ],
            },
            indent_step: 2,
            integrity_violations: Vec::new(),
        }
    }

    #[test]
    fn test_harmonize_deployment_controller_defaults() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_manifest("Deployment", "api-gateway", vec![]);

        let changes = heal_gitops_manifest(&mut manifest, &mut telemetry);
        assert_eq!(changes.len(), 3); // revisionHistoryLimit + progressDeadlineSeconds + sync-wave

        let spec = manifest.root.find_node("spec").unwrap();
        assert_eq!(
            spec.find_value("revisionHistoryLimit"),
            Some("10".to_string())
        );
        assert_eq!(
            spec.find_value("progressDeadlineSeconds"),
            Some("600".to_string())
        );

        let wave = manifest
            .root
            .find_annotation("argocd.argoproj.io/sync-wave");
        assert_eq!(wave, Some("\"0\"".to_string()));
    }

    #[test]
    fn test_stamp_crd_sync_wave() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_manifest(
            "CustomResourceDefinition",
            "certificates.cert-manager.io",
            vec![],
        );

        let changes = heal_gitops_manifest(&mut manifest, &mut telemetry);
        assert!(!changes.is_empty());

        let wave = manifest
            .root
            .find_annotation("argocd.argoproj.io/sync-wave");
        assert_eq!(wave, Some("\"-2\"".to_string()));
    }

    #[test]
    fn test_stamp_configmap_sync_wave() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_manifest("ConfigMap", "app-config", vec![]);

        let changes = heal_gitops_manifest(&mut manifest, &mut telemetry);
        assert!(!changes.is_empty());

        let wave = manifest
            .root
            .find_annotation("argocd.argoproj.io/sync-wave");
        assert_eq!(wave, Some("\"-1\"".to_string()));
    }

    #[test]
    fn test_stamp_test_job_sync_wave() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_manifest("Job", "integration-test-job", vec![]);

        let changes = heal_gitops_manifest(&mut manifest, &mut telemetry);
        assert!(!changes.is_empty());

        let wave = manifest
            .root
            .find_annotation("argocd.argoproj.io/sync-wave");
        assert_eq!(wave, Some("\"1\"".to_string()));
    }

    #[test]
    fn test_preserve_existing_sync_wave() {
        let mut telemetry = NativeTelemetry::default();
        let mut manifest = create_manifest("Deployment", "custom-wave-app", vec![]);
        set_annotation(&mut manifest.root, "argocd.argoproj.io/sync-wave", "\"5\"");

        let changes = heal_gitops_manifest(&mut manifest, &mut telemetry);
        // Defaults injected, but sync wave preserved
        let wave = manifest
            .root
            .find_annotation("argocd.argoproj.io/sync-wave");
        assert_eq!(wave, Some("\"5\"".to_string()));
        assert!(changes
            .iter()
            .all(|c| !c.contains("argocd.argoproj.io/sync-wave")));
    }
}
