//! Cross-resource GitOps sync-wave inversion hazard detector (Rule GTO-003).
//!
//! Why: In GitOps deployments (ArgoCD / Flux), sync waves dictate the strict phase order
//! of resource application. If a workload (Deployment/StatefulSet/Job) specifies a sync-wave
//! that is less than or equal to the wave of a dependency it consumes (Namespace, Secret,
//! ConfigMap), the workload controller attempts to create pods before the required configuration
//! exists in etcd, triggering immediate CrashLoopBackOff or admission rejection.

use crate::models::{IntegrityViolation, NativeIdentity};

pub struct GitopsWaveAuditor;

impl GitopsWaveAuditor {
    /// Detects sync-wave inversions across a fleet of resources.
    pub fn audit_sync_wave_inversions(identities: &[NativeIdentity]) -> Vec<IntegrityViolation> {
        let mut violations = Vec::new();

        // 1. Build map of dependency waves: (kind, namespace, name) -> wave
        let mut dependency_waves: std::collections::HashMap<(String, String, String), i32> =
            std::collections::HashMap::new();

        for id in identities {
            let wave_opt = id
                .annotations
                .get("argocd.argoproj.io/sync-wave")
                .or_else(|| id.annotations.get("yamlr.io/sync-wave"))
                .and_then(|w| w.trim_matches('"').parse::<i32>().ok());

            if let Some(wave) = wave_opt {
                dependency_waves.insert(
                    (id.kind.clone(), id.namespace.clone(), id.name.clone()),
                    wave,
                );
            }
        }

        // 2. Audit workloads consuming ConfigMaps or Secrets
        for id in identities {
            if ![
                "Deployment",
                "StatefulSet",
                "DaemonSet",
                "Job",
                "CronJob",
                "Pod",
            ]
            .contains(&id.kind.as_str())
            {
                continue;
            }

            let workload_wave = id
                .annotations
                .get("argocd.argoproj.io/sync-wave")
                .or_else(|| id.annotations.get("yamlr.io/sync-wave"))
                .and_then(|w| w.trim_matches('"').parse::<i32>().ok())
                .unwrap_or(0);

            let resource_id = format!("{}/{}/{}", id.kind, id.namespace, id.name);

            // Check referenced ConfigMaps
            for cfg in &id.config_refs {
                if let Some(&dep_wave) = dependency_waves.get(&(
                    "ConfigMap".to_string(),
                    id.namespace.clone(),
                    cfg.clone(),
                )) {
                    if workload_wave <= dep_wave {
                        violations.push(IntegrityViolation {
                            check_name: "SYNC-WAVE-INVERSION".to_string(),
                            severity: "ERROR".to_string(),
                            rule_id: "GTO-003".to_string(),
                            message: format!(
                                "GitOps Hazard: Workload '{}' has sync-wave {} which is <= required ConfigMap '{}' (sync-wave {}). Workload will fail to mount config at deploy time.",
                                resource_id, workload_wave, cfg, dep_wave
                            ),
                            line_no: 0,
                        });
                    }
                }
            }

            // Check referenced Secrets
            for sec in &id.secret_refs {
                if let Some(&dep_wave) =
                    dependency_waves.get(&("Secret".to_string(), id.namespace.clone(), sec.clone()))
                {
                    if workload_wave <= dep_wave {
                        violations.push(IntegrityViolation {
                            check_name: "SYNC-WAVE-INVERSION".to_string(),
                            severity: "ERROR".to_string(),
                            rule_id: "GTO-003".to_string(),
                            message: format!(
                                "GitOps Hazard: Workload '{}' has sync-wave {} which is <= required Secret '{}' (sync-wave {}). Workload will crash on missing secret mount.",
                                resource_id, workload_wave, sec, dep_wave
                            ),
                            line_no: 0,
                        });
                    }
                }
            }
        }

        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn test_sync_wave_inversion_detected() {
        let mut cfg_ann = HashMap::new();
        cfg_ann.insert("argocd.argoproj.io/sync-wave".to_string(), "0".to_string());

        let cfg = NativeIdentity {
            name: "app-config".into(),
            kind: "ConfigMap".into(),
            namespace: "prod".into(),
            annotations: cfg_ann,
            ..Default::default()
        };

        let mut deploy_ann = HashMap::new();
        deploy_ann.insert("argocd.argoproj.io/sync-wave".to_string(), "0".to_string());

        let deploy = NativeIdentity {
            name: "web-app".into(),
            kind: "Deployment".into(),
            namespace: "prod".into(),
            config_refs: vec!["app-config".into()],
            annotations: deploy_ann,
            ..Default::default()
        };

        let violations = GitopsWaveAuditor::audit_sync_wave_inversions(&[cfg, deploy]);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "GTO-003");
        assert!(violations[0].message.contains("web-app"));
    }

    #[test]
    fn test_sync_wave_proper_order_no_violation() {
        let mut cfg_ann = HashMap::new();
        cfg_ann.insert("argocd.argoproj.io/sync-wave".to_string(), "-1".to_string());

        let cfg = NativeIdentity {
            name: "app-config".into(),
            kind: "ConfigMap".into(),
            namespace: "prod".into(),
            annotations: cfg_ann,
            ..Default::default()
        };

        let mut deploy_ann = HashMap::new();
        deploy_ann.insert("argocd.argoproj.io/sync-wave".to_string(), "0".to_string());

        let deploy = NativeIdentity {
            name: "web-app".into(),
            kind: "Deployment".into(),
            namespace: "prod".into(),
            config_refs: vec!["app-config".into()],
            annotations: deploy_ann,
            ..Default::default()
        };

        let violations = GitopsWaveAuditor::audit_sync_wave_inversions(&[cfg, deploy]);
        assert!(violations.is_empty());
    }
}
