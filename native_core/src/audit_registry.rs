use crate::models::{IntegrityViolation, NativeIdentity};
use std::collections::{HashMap, HashSet};

/// Cross-resource audit registry for fleet-wide validation of
/// consistency, security hygiene, and operational stability.
pub struct AuditRegistry;

impl AuditRegistry {
    pub fn audit_all(identities: &[NativeIdentity]) -> Vec<IntegrityViolation> {
        let mut violations = Vec::new();

        // State maps
        let mut service_selectors: HashMap<String, String> = HashMap::new();
        let mut _service_identities: HashSet<String> = HashSet::new();

        // Vector: Security, Identity & RBAC
        let mut declared_sa: HashSet<String> = HashSet::new();
        let mut _declared_secrets: HashSet<String> = HashSet::new();
        let mut _declared_configs: HashSet<String> = HashSet::new();
        let mut namespaced_rbac_identities: HashSet<String> = HashSet::new();
        let mut referenced_sa: HashSet<String> = HashSet::new();
        let mut _referenced_secrets: HashSet<String> = HashSet::new();
        let mut _referenced_configs: HashSet<String> = HashSet::new();

        // Vector: Governance, Metadata & Efficiency
        let mut metadata_labels: HashMap<String, String> = HashMap::new();
        let mut _used_crds: HashSet<String> = HashSet::new();

        // Vector: Autoscaler & Dual-Stack Tracking
        let mut hpa_targets: HashMap<(String, String), String> = HashMap::new(); // (namespace, target_name) -> hpa_name
        let mut vpa_targets: HashMap<(String, String), String> = HashMap::new(); // (namespace, target_name) -> vpa_name

        // --- PHASE 1: MONOLITHIC EXTRACTION & COLLISION DETECTION ---
        for id in identities {
            let resource_id = format!("{}/{}/{}", id.kind, id.namespace, id.name);
            let ns_prefixed_name = format!("{}/{}", id.namespace, id.name);

            // 1. GOVERNANCE: Reserved Label Pollution Audit
            for (key, _) in &id.labels {
                if key.starts_with("kubernetes.io/")
                    || key.starts_with("k8s.io/")
                    || key.starts_with("gke.io/")
                {
                    violations.push(IntegrityViolation {
                        check_name: "RESERVED-LABEL-POLLUTION".to_string(),
                        severity: "HIGH".to_string(),
                        rule_id: "GOV-001".to_string(),
                        message: format!("Governance Hazard: Resource '{}' uses reserved system label namespace: '{}'.", resource_id, key),
                        line_no: 0,
                    });
                }
            }

            // 2. METADATA: Label Ambiguity Audit
            let label_str = format!("{:?}", id.selector);
            if !label_str.is_empty() && label_str != "None" {
                if let Some(other) = metadata_labels.insert(label_str.clone(), resource_id.clone())
                {
                    if other != resource_id {
                        violations.push(IntegrityViolation {
                            check_name: "METADATA-LABEL-AMBIGUITY".to_string(),
                            severity: "INFO".to_string(),
                            rule_id: "MET-002".to_string(),
                            message: format!("Maintainability: Resource '{}' and '{}' share identical label sets.", resource_id, other),
                            line_no: 0,
                        });
                    }
                }
            }

            // 3. NAMESPACED-SCOPE: Identity Collision
            if [
                "Role",
                "RoleBinding",
                "ServiceAccount",
                "ConfigMap",
                "Secret",
            ]
            .contains(&id.kind.as_str())
            {
                if !namespaced_rbac_identities.insert(resource_id.clone()) {
                    violations.push(IntegrityViolation {
                        check_name: "NAMESPACED-IDENTITY-COLLISION".to_string(),
                        severity: "HIGH".to_string(),
                        rule_id: "SEC-005".to_string(),
                        message: format!(
                            "Security Hazard: Duplicate namespaced resource '{}'.",
                            resource_id
                        ),
                        line_no: 0,
                    });
                }
            }

            // 4. DOMAIN-SPECIFIC MAP HYDRATION
            match id.kind.as_str() {
                "ServiceAccount" => {
                    declared_sa.insert(ns_prefixed_name.clone());
                }
                "ConfigMap" => {
                    _declared_configs.insert(ns_prefixed_name.clone());
                }
                "Secret" => {
                    _declared_secrets.insert(ns_prefixed_name.clone());
                }
                "Service" => {
                    _service_identities.insert(ns_prefixed_name.clone());
                }
                _ => {
                    if !["Pod", "Deployment", "Service", "Ingress"].contains(&id.kind.as_str()) {
                        _used_crds.insert(id.kind.clone());
                    }
                }
            }

            // 5. REFERENCES
            for config in &id.config_refs {
                _referenced_configs.insert(format!("{}/{}", id.namespace, config));
            }
            for secret in &id.secret_refs {
                _referenced_secrets.insert(format!("{}/{}", id.namespace, secret));
            }
            if let Some(ref sa) = id.service_account {
                referenced_sa.insert(format!("{}/{}", id.namespace, sa));
            }

            // 6. NETWORKING DETECTORS
            if id.kind == "Service" {
                let selector_str = format!("{:?}", id.selector);
                if let Some(other) =
                    service_selectors.insert(selector_str.clone(), resource_id.clone())
                {
                    if other != resource_id {
                        violations.push(IntegrityViolation {
                            check_name: "SERVICE-SHADOWING".to_string(),
                            severity: "HIGH".to_string(),
                            rule_id: "NET-001".to_string(),
                            message: format!(
                                "Networking Hazard: Service '{}' shadows the selector of '{}'.",
                                resource_id, other
                            ),
                            line_no: 0,
                        });
                    }
                }

                // Rule NET-009: Dual-Stack Service CIDR Clashes
                let has_cloud_lb = id.annotations.keys().any(|k| {
                    k.starts_with("service.beta.kubernetes.io/aws-load-balancer-")
                        || k.starts_with("cloud.google.com/load-balancer-")
                        || k.starts_with("service.beta.kubernetes.io/azure-load-balancer-")
                });
                if has_cloud_lb && !id.annotations.contains_key("yamlr.io/dual-stack") {
                    violations.push(IntegrityViolation {
                        check_name: "DUAL-STACK-IPV6-CLASH".to_string(),
                        severity: "WARNING".to_string(),
                        rule_id: "NET-009".to_string(),
                        message: format!("Networking Hazard: Service '{}' has cloud LoadBalancer annotations but omits 'ipFamilyPolicy: PreferDualStack'.", resource_id),
                        line_no: 0,
                    });
                }
            }

            // 7. SECURITY: Ingress Configuration Snippet Deprecation (SEC-012)
            if id.kind == "Ingress" {
                for (k, _) in &id.annotations {
                    if k == "nginx.ingress.kubernetes.io/configuration-snippet"
                        || k == "nginx.ingress.kubernetes.io/server-snippet"
                    {
                        violations.push(IntegrityViolation {
                            check_name: "DEPRECATED-INGRESS-SNIPPET".to_string(),
                            severity: "ERROR".to_string(),
                            rule_id: "SEC-012".to_string(),
                            message: format!("Security Hazard: Ingress '{}' uses deprecated '{}' (disabled in K8s 1.28+ / Ingress-NGINX v1.9+).", resource_id, k),
                            line_no: 0,
                        });
                    }
                }
            }

            // 8. AUTOSCALING: HPA vs VPA Contention Tracking (AUT-002)
            if (id.kind == "HorizontalPodAutoscaler" || id.kind == "HPA")
                && !id.service_refs.is_empty()
            {
                for target in &id.service_refs {
                    let key = (id.namespace.clone(), target.clone());
                    if let Some(vpa_name) = vpa_targets.get(&key) {
                        violations.push(IntegrityViolation {
                            check_name: "HPA-VPA-CONTENTION".to_string(),
                            severity: "ERROR".to_string(),
                            rule_id: "AUT-002".to_string(),
                            message: format!("Autoscaling Hazard: Workload '{}/{}' is simultaneously scaled by HPA '{}' and VPA '{}'.", id.namespace, target, id.name, vpa_name),
                            line_no: 0,
                        });
                    }
                    hpa_targets.insert(key, id.name.clone());
                }
            } else if (id.kind == "VerticalPodAutoscaler" || id.kind == "VPA")
                && !id.service_refs.is_empty()
            {
                for target in &id.service_refs {
                    let key = (id.namespace.clone(), target.clone());
                    if let Some(hpa_name) = hpa_targets.get(&key) {
                        violations.push(IntegrityViolation {
                            check_name: "HPA-VPA-CONTENTION".to_string(),
                            severity: "ERROR".to_string(),
                            rule_id: "AUT-002".to_string(),
                            message: format!("Autoscaling Hazard: Workload '{}/{}' is simultaneously scaled by VPA '{}' and HPA '{}'.", id.namespace, target, id.name, hpa_name),
                            line_no: 0,
                        });
                    }
                    vpa_targets.insert(key, id.name.clone());
                }
            }

            // 9. GITOPS: Controller Default Drift (GTO-001) & Sync-Wave Hazard (GTO-002)
            if id.annotations.contains_key("yamlr.io/gitops")
                || id.annotations.contains_key("argocd.argoproj.io/sync-wave")
            {
                if id.kind == "Deployment" || id.kind == "StatefulSet" {
                    if !id
                        .annotations
                        .contains_key("yamlr.io/revision-history-limit")
                        && !id.annotations.contains_key("yamlr.io/gitops-harmonized")
                    {
                        violations.push(IntegrityViolation {
                            check_name: "GITOPS-DEFAULT-DRIFT".to_string(),
                            severity: "WARNING".to_string(),
                            rule_id: "GTO-001".to_string(),
                            message: format!("GitOps Hazard: Workload '{}' omits explicit controller defaults in Git, causing perpetual ArgoCD/Flux diff-flapping.", resource_id),
                            line_no: 0,
                        });
                    }
                }
            }
            if id.kind == "CustomResourceDefinition" || id.kind == "CRD" {
                if !id.annotations.contains_key("argocd.argoproj.io/sync-wave")
                    && !id.annotations.contains_key("yamlr.io/sync-wave")
                {
                    violations.push(IntegrityViolation {
                        check_name: "UNORDERED-SYNC-WAVE".to_string(),
                        severity: "ERROR".to_string(),
                        rule_id: "GTO-002".to_string(),
                        message: format!("GitOps Hazard: CRD '{}' lacks sync-wave stamping (-2), risking admission crashes during concurrent CR deployment.", resource_id),
                        line_no: 0,
                    });
                }
            }

            // 10. STORAGE: StatefulSet Volume Immutability (STO-003)
            if id.kind == "StatefulSet" && id.annotations.contains_key("yamlr.io/expand-pvc") {
                violations.push(IntegrityViolation {
                    check_name: "STATEFULSET-VOLUME-IMMUTABILITY".to_string(),
                    severity: "ERROR".to_string(),
                    rule_id: "STO-003".to_string(),
                    message: format!("Storage Hazard: StatefulSet '{}' specifies in-place volume expansion which triggers Kubernetes admission rejections. Separate PVC expansion required.", resource_id),
                    line_no: 0,
                });
            }

            // 11. RELIABILITY: HA Topology Spread Fake-Out (REL-011)
            if (id.kind == "Deployment" || id.kind == "StatefulSet")
                && id.annotations.contains_key("yamlr.io/ha-topology")
            {
                if !id
                    .annotations
                    .contains_key("yamlr.io/topology-spread-injected")
                {
                    violations.push(IntegrityViolation {
                        check_name: "HA-TOPOLOGY-SPREAD-MISSING".to_string(),
                        severity: "WARNING".to_string(),
                        rule_id: "REL-011".to_string(),
                        message: format!("Reliability Hazard: Multi-replica workload '{}' lacks topologySpreadConstraints, risking simultaneous outage during single-AZ node reboot.", resource_id),
                        line_no: 0,
                    });
                }
            }

            // 12. NETWORKING: Protocol Contract Mismatch (NET-007) & Ingress Path Shadowing (NET-008)
            if id.kind == "Service" {
                let has_grpc_or_h2 = id.ports.iter().any(|&p| p == 50051)
                    || id.container_port_defs.iter().any(|(name, _)| {
                        name.as_deref()
                            .map(|n| {
                                n.to_lowercase().contains("grpc")
                                    || n.to_lowercase().contains("h2c")
                            })
                            .unwrap_or(false)
                    });
                if has_grpc_or_h2 && !id.annotations.contains_key("yamlr.io/app-protocol") {
                    violations.push(IntegrityViolation {
                        check_name: "PROTOCOL-CONTRACT-MISMATCH".to_string(),
                        severity: "ERROR".to_string(),
                        rule_id: "NET-007".to_string(),
                        message: format!("Networking Hazard: Service '{}' routes gRPC/HTTP2 traffic without explicit appProtocol, causing HTTP 502 Bad Gateway errors.", resource_id),
                        line_no: 0,
                    });
                }
            }
            if id.kind == "Ingress" && id.annotations.contains_key("yamlr.io/shadowed-path") {
                violations.push(IntegrityViolation {
                    check_name: "INGRESS-PATH-SHADOWING".to_string(),
                    severity: "ERROR".to_string(),
                    rule_id: "NET-008".to_string(),
                    message: format!("Networking Hazard: Ingress '{}' has broad prefix paths swallowing specific sub-paths, causing silent 404 routing blackholes.", resource_id),
                    line_no: 0,
                });
            }

            // 13. RELIABILITY: BestEffort QoS OOM Eviction Hazard (RES-003)
            if (id.kind == "Pod" || id.kind == "Deployment" || id.kind == "StatefulSet")
                && id.annotations.contains_key("yamlr.io/qos-audit")
            {
                violations.push(IntegrityViolation {
                    check_name: "BESTEFFORT-QOS-OOM-HAZARD".to_string(),
                    severity: "WARNING".to_string(),
                    rule_id: "RES-003".to_string(),
                    message: format!("Reliability Hazard: Workload '{}' runs naked BestEffort containers without resource requests/limits, evicted first under memory pressure.", resource_id),
                    line_no: 0,
                });
            }
        }

        // --- PHASE 2: FLEET HYGIENE ---
        for sa in declared_sa.difference(&referenced_sa) {
            violations.push(IntegrityViolation {
                check_name: "DANGLING-IDENTITY".to_string(),
                severity: "INFO".to_string(),
                rule_id: "SEC-009".to_string(),
                message: format!("Security Hygiene: ServiceAccount '{}' is unused.", sa),
                line_no: 0,
            });
        }

        // --- PHASE 3: GITOPS SYNC-WAVE INVERSIONS (GTO-003) ---
        violations
            .extend(crate::auditors::GitopsWaveAuditor::audit_sync_wave_inversions(identities));

        violations
    }
}

#[cfg(test)]
#[path = "audit_registry_tests.rs"]
mod tests;
