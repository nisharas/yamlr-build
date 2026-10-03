//! Broken Reference Fuzzy Alignment Engine (Feature 7 of 15).
//!
//! Why: Pods referencing misspelled ConfigMaps, Secrets, or PVCs (e.g. `configMapRef.name: app-confg`
//! vs `ConfigMap: app-config`) enter permanent `CreateContainerConfigError` or `CrashLoopBackOff`.
//!
//! This module searches the AST for ConfigMap, Secret, and PVC references, checks them against
//! known workspace resource definitions, and auto-corrects typos to restore working bindings.

use crate::models::{NativeIdentity, NativeTelemetry, SemanticManifest, SemanticNode};
use crate::telemetry::native_record_healing_impact;

pub static REF_SIMILARITY_THRESHOLD: f64 = 0.70;

/// Recursively finds and aligns broken resource references in an AST node.
fn align_refs_recursive(
    node: &mut SemanticNode,
    ns: &str,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
    changes: &mut Vec<String>,
) {
    let key_lower = node.key.to_lowercase();

    // 1. ConfigMap reference
    if key_lower == "configmapref" || key_lower == "configmapkeyref" {
        if let Some(name_node) = node.find_node_mut("name") {
            let current_name = name_node.value.clone().unwrap_or_default();
            if !current_name.is_empty() {
                let cms: Vec<&NativeIdentity> = identities
                    .iter()
                    .filter(|id| id.kind == "ConfigMap" && id.namespace == ns)
                    .collect();

                if !cms.is_empty() && !cms.iter().any(|c| c.name == current_name) {
                    let mut best_target = None;
                    let mut best_ratio = 0.0;
                    for cm in cms {
                        let is_kustomize_match = cm.name.len() == current_name.len() + 11
                            && cm.name.starts_with(&current_name)
                            && cm.name.chars().nth(current_name.len()) == Some('-')
                            && cm.name[current_name.len() + 1..]
                                .chars()
                                .all(|c| c.is_ascii_alphanumeric());

                        if is_kustomize_match {
                            best_target = Some(cm);
                            best_ratio = 1.0;
                            break;
                        }

                        let ratio = crate::healers::selector_healer::similarity_ratio(
                            &current_name,
                            &cm.name,
                        );
                        if ratio >= REF_SIMILARITY_THRESHOLD && ratio > best_ratio {
                            best_ratio = ratio;
                            best_target = Some(cm);
                        }
                    }

                    if let Some(target) = best_target {
                        name_node.value = Some(target.name.clone());
                        for s in &mut name_node.shards {
                            s.value = Some(target.name.clone());
                        }
                        let msg = format!(
                            "Remediation [REF-001]: Aligned ConfigMap reference '{}' -> '{}' (similarity: {:.2}).",
                            current_name, target.name, best_ratio
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    }

    // 2. Secret reference
    if key_lower == "secretref" || key_lower == "secretkeyref" {
        if let Some(name_node) = node.find_node_mut("name") {
            let current_name = name_node.value.clone().unwrap_or_default();
            if !current_name.is_empty() {
                let secrets: Vec<&NativeIdentity> = identities
                    .iter()
                    .filter(|id| id.kind == "Secret" && id.namespace == ns)
                    .collect();

                if !secrets.is_empty() && !secrets.iter().any(|s| s.name == current_name) {
                    let mut best_target = None;
                    let mut best_ratio = 0.0;
                    for s in secrets {
                        let is_kustomize_match = s.name.len() == current_name.len() + 11
                            && s.name.starts_with(&current_name)
                            && s.name.chars().nth(current_name.len()) == Some('-')
                            && s.name[current_name.len() + 1..]
                                .chars()
                                .all(|c| c.is_ascii_alphanumeric());

                        if is_kustomize_match {
                            best_target = Some(s);
                            best_ratio = 1.0;
                            break;
                        }

                        let ratio = crate::healers::selector_healer::similarity_ratio(
                            &current_name,
                            &s.name,
                        );
                        if ratio >= REF_SIMILARITY_THRESHOLD && ratio > best_ratio {
                            best_ratio = ratio;
                            best_target = Some(s);
                        }
                    }

                    if let Some(target) = best_target {
                        name_node.value = Some(target.name.clone());
                        for s in &mut name_node.shards {
                            s.value = Some(target.name.clone());
                        }
                        let msg = format!(
                            "Remediation [REF-001]: Aligned Secret reference '{}' -> '{}' (similarity: {:.2}).",
                            current_name, target.name, best_ratio
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    }

    // 3. PersistentVolumeClaim reference
    if key_lower == "persistentvolumeclaim" {
        if let Some(claim_node) = node.find_node_mut("claimName") {
            let current_name = claim_node.value.clone().unwrap_or_default();
            if !current_name.is_empty() {
                let pvcs: Vec<&NativeIdentity> = identities
                    .iter()
                    .filter(|id| id.kind == "PersistentVolumeClaim" && id.namespace == ns)
                    .collect();

                if !pvcs.is_empty() && !pvcs.iter().any(|p| p.name == current_name) {
                    let mut best_target = None;
                    let mut best_ratio = 0.0;
                    for p in pvcs {
                        let ratio = crate::healers::selector_healer::similarity_ratio(
                            &current_name,
                            &p.name,
                        );
                        if ratio >= REF_SIMILARITY_THRESHOLD && ratio > best_ratio {
                            best_ratio = ratio;
                            best_target = Some(p);
                        }
                    }

                    if let Some(target) = best_target {
                        claim_node.value = Some(target.name.clone());
                        for s in &mut claim_node.shards {
                            s.value = Some(target.name.clone());
                        }
                        let msg = format!(
                            "Remediation [REF-001]: Aligned PVC reference '{}' -> '{}' (similarity: {:.2}).",
                            current_name, target.name, best_ratio
                        );
                        native_record_healing_impact(telemetry, &msg);
                        changes.push(msg);
                    }
                }
            }
        }
    }

    // Recurse into children
    for child in &mut node.children {
        align_refs_recursive(child, ns, identities, telemetry, changes);
    }
}

/// Primary Entrypoint: Aligns all broken ConfigMap, Secret, and PVC references in a manifest.
pub fn heal_referential_links(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    align_refs_recursive(&mut manifest.root, &ns, identities, telemetry, &mut changes);

    changes.extend(heal_ingress_backend_mismatch(
        manifest, identities, telemetry,
    ));
    changes.extend(heal_hpa_target_mismatch(manifest, identities, telemetry));

    changes
}

/// Heals Ingress backend service references if misspelled.
pub fn heal_ingress_backend_mismatch(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "Ingress" {
        return changes;
    }

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    let services: Vec<&NativeIdentity> = identities
        .iter()
        .filter(|id| id.kind == "Service" && id.namespace == ns)
        .collect();

    if services.is_empty() {
        return changes;
    }

    for svc_node in manifest.root.find_nodes_by_key_recursive_mut("service") {
        if let Some(name_node) = svc_node.find_node_mut("name") {
            if let Some(ref cur) = name_node.value {
                let current_name = cur
                    .trim()
                    .trim_matches(|c| c == '\'' || c == '"')
                    .to_string();
                if !services.iter().any(|s| s.name == current_name) {
                    let mut best_match = None;
                    let mut best_ratio = 0.0;
                    for s in &services {
                        let ratio = crate::healers::selector_healer::similarity_ratio(
                            &current_name,
                            &s.name,
                        );
                        if ratio >= REF_SIMILARITY_THRESHOLD && ratio > best_ratio {
                            best_ratio = ratio;
                            best_match = Some(s);
                        }
                    }
                    if let Some(target) = best_match {
                        name_node.value = Some(target.name.clone());
                        for s in &mut name_node.shards {
                            s.value = Some(target.name.clone());
                        }
                        let msg = format!(
                            "Remediation [REF-002]: Aligned Ingress backend service '{}' -> '{}' (similarity: {:.2}).",
                            current_name, target.name, best_ratio
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

/// Heals HorizontalPodAutoscaler scaleTargetRef mismatches.
pub fn heal_hpa_target_mismatch(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    let mut changes = Vec::new();
    let kind = manifest.root.find_value("kind").unwrap_or_default();
    if kind != "HorizontalPodAutoscaler" {
        return changes;
    }

    let ns = manifest
        .root
        .find_node("metadata")
        .and_then(|m| m.find_value("namespace"))
        .unwrap_or_else(|| "default".to_string());

    if let Some(spec) = manifest.root.find_node_mut("spec") {
        if let Some(target_ref) = spec.find_node_mut("scaleTargetRef") {
            let target_kind = target_ref
                .find_value("kind")
                .unwrap_or_else(|| "Deployment".to_string());
            if let Some(name_node) = target_ref.find_node_mut("name") {
                if let Some(ref cur) = name_node.value {
                    let current_name = cur
                        .trim()
                        .trim_matches(|c| c == '\'' || c == '"')
                        .to_string();
                    let workloads: Vec<&NativeIdentity> = identities
                        .iter()
                        .filter(|id| id.kind == target_kind && id.namespace == ns)
                        .collect();

                    if !workloads.is_empty() && !workloads.iter().any(|w| w.name == current_name) {
                        let mut best_match = None;
                        let mut best_ratio = 0.0;
                        for w in workloads {
                            let ratio = crate::healers::selector_healer::similarity_ratio(
                                &current_name,
                                &w.name,
                            );
                            if ratio >= REF_SIMILARITY_THRESHOLD && ratio > best_ratio {
                                best_ratio = ratio;
                                best_match = Some(w);
                            }
                        }
                        if let Some(target) = best_match {
                            name_node.value = Some(target.name.clone());
                            for s in &mut name_node.shards {
                                s.value = Some(target.name.clone());
                            }
                            let msg = format!(
                                "Remediation [REF-003]: Aligned HPA scaleTargetRef '{}' -> '{}' (similarity: {:.2}).",
                                current_name, target.name, best_ratio
                            );
                            native_record_healing_impact(telemetry, &msg);
                            changes.push(msg);
                        }
                    }
                }
            }
        }
    }

    changes
}

/// Heals Service selector label mismatches if misspelled.
pub fn heal_service_selector_mismatch(
    manifest: &mut SemanticManifest,
    identities: &[NativeIdentity],
    telemetry: &mut NativeTelemetry,
) -> Vec<String> {
    crate::healers::selector_healer::heal_service_selectors_with_identities(
        manifest, identities, telemetry,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_align_broken_configmap_ref() {
        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();

        let mut node = SemanticNode {
            key: "configMapRef".to_string(),
            value: None,
            indent: 4,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "name".to_string(),
                value: Some("app-confg".to_string()),
                indent: 6,
                is_empty_flow: false,
                children: Vec::new(),
                shards: Vec::new(),
            }],
        };

        let target_cm = NativeIdentity {
            kind: "ConfigMap".to_string(),
            api_version: Some("v1".to_string()),
            name: "app-config".to_string(),
            namespace: "default".to_string(),
            owner_refs: Vec::new(),
            labels: std::collections::HashMap::new(),
            selector: std::collections::HashMap::new(),
            config_refs: Vec::new(),
            secret_refs: Vec::new(),
            volume_refs: Vec::new(),
            service_refs: Vec::new(),
            role_refs: Vec::new(),
            cluster_role_refs: Vec::new(),
            service_account: None,
            shadow_fingerprint: String::new(),
            relationships: Vec::new(),
            ports: Vec::new(),
            ..Default::default()
        };

        let ids = vec![target_cm];
        align_refs_recursive(&mut node, "default", &ids, &mut telemetry, &mut changes);

        assert_eq!(
            node.find_node("name").unwrap().value,
            Some("app-config".to_string())
        );
        assert_eq!(changes.len(), 1);
    }

    #[test]
    fn test_align_kustomize_hashed_configmap() {
        let mut telemetry = NativeTelemetry::default();
        let mut changes = Vec::new();

        let mut node = SemanticNode {
            key: "configMapRef".to_string(),
            value: None,
            indent: 4,
            is_empty_flow: false,
            shards: Vec::new(),
            children: vec![SemanticNode {
                key: "name".to_string(),
                value: Some("game-config".to_string()),
                indent: 6,
                is_empty_flow: false,
                children: Vec::new(),
                shards: Vec::new(),
            }],
        };

        // Kustomize generated configmap name with 10-char hash suffix
        let target_cm = NativeIdentity {
            kind: "ConfigMap".to_string(),
            api_version: Some("v1".to_string()),
            name: "game-config-k8b244d2k9".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };

        let ids = vec![target_cm];
        align_refs_recursive(&mut node, "default", &ids, &mut telemetry, &mut changes);

        assert_eq!(
            node.find_node("name").unwrap().value,
            Some("game-config-k8b244d2k9".to_string())
        );
        assert_eq!(changes.len(), 1);
    }

    #[test]
    fn test_align_ingress_backend_mismatch() {
        let mut telemetry = NativeTelemetry::default();
        let yaml = r#"
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ing
  namespace: prod
spec:
  rules:
    - http:
        paths:
          - backend:
              service:
                name: frontend-svrc
"#;
        let mut manifest =
            crate::structurer::native_structurize(crate::sharder::native_shard(yaml));
        let target_svc = NativeIdentity {
            kind: "Service".to_string(),
            name: "frontend-svc".to_string(),
            namespace: "prod".to_string(),
            ..Default::default()
        };

        let changes = heal_ingress_backend_mismatch(&mut manifest, &[target_svc], &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("frontend-svrc' -> 'frontend-svc"));
    }

    #[test]
    fn test_align_hpa_target_mismatch() {
        let mut telemetry = NativeTelemetry::default();
        let yaml = r#"
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-ap
"#;
        let mut manifest =
            crate::structurer::native_structurize(crate::sharder::native_shard(yaml));
        let target_deploy = NativeIdentity {
            kind: "Deployment".to_string(),
            name: "web-app".to_string(),
            namespace: "default".to_string(),
            ..Default::default()
        };

        let changes = heal_hpa_target_mismatch(&mut manifest, &[target_deploy], &mut telemetry);
        assert_eq!(changes.len(), 1);
        assert!(changes[0].contains("web-ap' -> 'web-app"));
    }
}
