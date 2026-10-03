//! Topology Graph Builder and Relational Edge Extractor.
//!
//! Why: Builds a directed dependency graph connecting Kubernetes resources across
//!      12 typed relationship categories using indexed lookups for O(N) performance.

use crate::models::{NativeDiscoveryResult, NativeEdge, NativeIdentity};
use std::collections::{HashMap, HashSet};

/// Pre-indexed catalog of Kubernetes resources for sub-millisecond edge resolution.
struct IndexedCatalog<'a> {
    _by_kind_ns: HashMap<(&'a str, &'a str), Vec<&'a NativeIdentity>>,
    by_kind_ns_name: HashMap<(&'a str, &'a str, &'a str), &'a NativeIdentity>,
    cluster_scoped_by_name: HashMap<(&'a str, &'a str), &'a NativeIdentity>,
    workloads_by_ns: HashMap<&'a str, Vec<&'a NativeIdentity>>,
}

impl<'a> IndexedCatalog<'a> {
    fn new(identities: &'a [NativeIdentity]) -> Self {
        let mut _by_kind_ns: HashMap<(&'a str, &'a str), Vec<&'a NativeIdentity>> = HashMap::new();
        let mut by_kind_ns_name: HashMap<(&'a str, &'a str, &'a str), &'a NativeIdentity> =
            HashMap::new();
        let mut cluster_scoped_by_name: HashMap<(&'a str, &'a str), &'a NativeIdentity> =
            HashMap::new();
        let mut workloads_by_ns: HashMap<&'a str, Vec<&'a NativeIdentity>> = HashMap::new();

        for id in identities {
            let kind = id.kind.as_str();
            let ns = id.namespace.as_str();
            let name = id.name.as_str();

            _by_kind_ns.entry((kind, ns)).or_default().push(id);
            by_kind_ns_name.insert((kind, ns, name), id);

            if is_cluster_scoped(kind) {
                cluster_scoped_by_name.insert((kind, name), id);
            }

            if is_workload(kind) {
                workloads_by_ns.entry(ns).or_default().push(id);
            }
        }

        Self {
            _by_kind_ns,
            by_kind_ns_name,
            cluster_scoped_by_name,
            workloads_by_ns,
        }
    }
}

fn is_cluster_scoped(kind: &str) -> bool {
    matches!(
        kind,
        "ClusterRole"
            | "ClusterRoleBinding"
            | "Namespace"
            | "Node"
            | "PersistentVolume"
            | "StorageClass"
            | "CustomResourceDefinition"
            | "ClusterIssuer"
            | "CiliumClusterwideNetworkPolicy"
    )
}

fn is_workload(kind: &str) -> bool {
    matches!(
        kind,
        "Deployment"
            | "StatefulSet"
            | "DaemonSet"
            | "Job"
            | "CronJob"
            | "Pod"
            | "ReplicaSet"
            | "Rollout"
            | "Workflow"
    )
}

fn format_key(id: &NativeIdentity) -> String {
    format!("{}/{}/{}", id.kind, id.namespace, id.name)
}

/// Builds all directed topology edges from an array of discovered identities.
pub fn build_topology_edges(identities: &[NativeIdentity]) -> Vec<NativeEdge> {
    let mut edges = Vec::new();
    let mut edge_keys = HashSet::new();
    let catalog = IndexedCatalog::new(identities);

    for r1 in identities {
        let r1_key = format_key(r1);
        let ns = r1.namespace.as_str();

        // 1. ConfigMap References
        for config in &r1.config_refs {
            if let Some(r2) = catalog
                .by_kind_ns_name
                .get(&("ConfigMap", ns, config.as_str()))
            {
                push_edge(
                    &mut edges,
                    &mut edge_keys,
                    &r1_key,
                    &format_key(r2),
                    "ConfigRef",
                );
            }
        }

        // 2. Secret References
        for secret in &r1.secret_refs {
            if let Some(r2) = catalog
                .by_kind_ns_name
                .get(&("Secret", ns, secret.as_str()))
            {
                push_edge(
                    &mut edges,
                    &mut edge_keys,
                    &r1_key,
                    &format_key(r2),
                    "SecretRef",
                );
            }
        }

        // 3. PersistentVolumeClaim References
        for pvc in &r1.volume_refs {
            if let Some(r2) =
                catalog
                    .by_kind_ns_name
                    .get(&("PersistentVolumeClaim", ns, pvc.as_str()))
            {
                push_edge(
                    &mut edges,
                    &mut edge_keys,
                    &r1_key,
                    &format_key(r2),
                    "PvcRef",
                );
            }
        }

        // 4. Service Account References
        if let Some(ref sa_name) = r1.service_account {
            if let Some(r2) = catalog
                .by_kind_ns_name
                .get(&("ServiceAccount", ns, sa_name.as_str()))
            {
                push_edge(
                    &mut edges,
                    &mut edge_keys,
                    &r1_key,
                    &format_key(r2),
                    "ServiceAccountRef",
                );
            }
        }

        // 5. Service Selector Matches
        if r1.kind == "Service" && !r1.selector.is_empty() {
            if let Some(workloads) = catalog.workloads_by_ns.get(ns) {
                for wl in workloads {
                    if labels_match(&r1.selector, &wl.labels) {
                        push_edge(
                            &mut edges,
                            &mut edge_keys,
                            &r1_key,
                            &format_key(wl),
                            "SelectorMatch",
                        );
                    }
                }
            }
        }

        // 6. Service Named and Numeric Port Binds
        if r1.kind == "Service" && !r1.ports.is_empty() {
            if let Some(workloads) = catalog.workloads_by_ns.get(ns) {
                for wl in workloads {
                    let has_matching_port = r1.ports.iter().any(|sp| wl.ports.contains(sp))
                        || r1.container_port_defs.iter().any(|(name_opt, p)| {
                            wl.container_port_defs.iter().any(|(wl_name_opt, wl_p)| {
                                (name_opt.is_some() && name_opt == wl_name_opt) || *p == *wl_p
                            })
                        });

                    if has_matching_port {
                        push_edge(
                            &mut edges,
                            &mut edge_keys,
                            &r1_key,
                            &format_key(wl),
                            "PortBind",
                        );
                    }
                }
            }
        }

        // 7. Ingress to Service Backends
        if r1.kind == "Ingress" {
            for svc_name in &r1.service_refs {
                if let Some(svc) = catalog
                    .by_kind_ns_name
                    .get(&("Service", ns, svc_name.as_str()))
                {
                    push_edge(
                        &mut edges,
                        &mut edge_keys,
                        &r1_key,
                        &format_key(svc),
                        "IngressBackend",
                    );
                }
            }
        }

        // 8. Role & ClusterRole Bindings
        if r1.kind == "RoleBinding" {
            for role_name in &r1.role_refs {
                if let Some(role) = catalog
                    .by_kind_ns_name
                    .get(&("Role", ns, role_name.as_str()))
                {
                    push_edge(
                        &mut edges,
                        &mut edge_keys,
                        &r1_key,
                        &format_key(role),
                        "RoleRef",
                    );
                } else if let Some(crole) = catalog
                    .cluster_scoped_by_name
                    .get(&("ClusterRole", role_name.as_str()))
                {
                    push_edge(
                        &mut edges,
                        &mut edge_keys,
                        &r1_key,
                        &format_key(crole),
                        "RoleRef",
                    );
                }
            }
        } else if r1.kind == "ClusterRoleBinding" {
            for role_name in &r1.cluster_role_refs {
                if let Some(crole) = catalog
                    .cluster_scoped_by_name
                    .get(&("ClusterRole", role_name.as_str()))
                {
                    push_edge(
                        &mut edges,
                        &mut edge_keys,
                        &r1_key,
                        &format_key(crole),
                        "RoleRef",
                    );
                }
            }
        }

        // 9. Autoscaling Target References (HPA & VPA)
        if (r1.kind == "HorizontalPodAutoscaler" || r1.kind == "HPA") && !r1.service_refs.is_empty()
        {
            for target_name in &r1.service_refs {
                if let Some(workloads) = catalog.workloads_by_ns.get(ns) {
                    for wl in workloads {
                        if wl.name == *target_name {
                            push_edge(
                                &mut edges,
                                &mut edge_keys,
                                &r1_key,
                                &format_key(wl),
                                "HpaTargetRef",
                            );
                        }
                    }
                }
            }
        } else if (r1.kind == "VerticalPodAutoscaler" || r1.kind == "VPA")
            && !r1.service_refs.is_empty()
        {
            for target_name in &r1.service_refs {
                if let Some(workloads) = catalog.workloads_by_ns.get(ns) {
                    for wl in workloads {
                        if wl.name == *target_name {
                            push_edge(
                                &mut edges,
                                &mut edge_keys,
                                &r1_key,
                                &format_key(wl),
                                "VpaTargetRef",
                            );

                            // Check if an HPA in the catalog targets this same workload -> create AutoscalerContention edge
                            if let Some(hpas) = catalog
                                ._by_kind_ns
                                .get(&("HorizontalPodAutoscaler", ns))
                                .or_else(|| catalog._by_kind_ns.get(&("HPA", ns)))
                            {
                                for hpa in hpas {
                                    if hpa.service_refs.contains(target_name) {
                                        let hpa_key = format_key(hpa);
                                        push_edge(
                                            &mut edges,
                                            &mut edge_keys,
                                            &r1_key,
                                            &hpa_key,
                                            "AutoscalerContention",
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // 10. PodDisruptionBudget & NetworkPolicy Selectors
        if (r1.kind == "PodDisruptionBudget" || r1.kind == "NetworkPolicy")
            && !r1.selector.is_empty()
        {
            let edge_type = if r1.kind == "PodDisruptionBudget" {
                "PdbRef"
            } else {
                "NetworkPolicyRef"
            };
            if let Some(workloads) = catalog.workloads_by_ns.get(ns) {
                for wl in workloads {
                    if labels_match(&r1.selector, &wl.labels) {
                        push_edge(
                            &mut edges,
                            &mut edge_keys,
                            &r1_key,
                            &format_key(wl),
                            edge_type,
                        );
                    }
                }
            }
        }

        // 11. Owner References (Child -> Parent)
        for owner in &r1.owner_refs {
            if let Some(workloads) = catalog.workloads_by_ns.get(ns) {
                for wl in workloads {
                    if wl.name == *owner {
                        push_edge(
                            &mut edges,
                            &mut edge_keys,
                            &r1_key,
                            &format_key(wl),
                            "OwnerRef",
                        );
                    }
                }
            }
        }
    }

    // Deterministic sorting for SARIF and CI reproducibility
    edges.sort_by(|a, b| {
        a.from_resource
            .cmp(&b.from_resource)
            .then_with(|| a.to_resource.cmp(&b.to_resource))
            .then_with(|| a.edge_type.cmp(&b.edge_type))
    });

    edges
}

fn labels_match(
    selector: &HashMap<String, String>,
    target_labels: &HashMap<String, String>,
) -> bool {
    if selector.is_empty() {
        return false;
    }
    selector
        .iter()
        .all(|(k, v)| target_labels.get(k) == Some(v))
}

fn push_edge(
    edges: &mut Vec<NativeEdge>,
    seen: &mut HashSet<(String, String, String)>,
    from: &str,
    to: &str,
    edge_type: &str,
) {
    let key = (from.to_string(), to.to_string(), edge_type.to_string());
    if seen.insert(key) {
        edges.push(NativeEdge {
            from_resource: from.to_string(),
            to_resource: to.to_string(),
            edge_type: edge_type.to_string(),
        });
    }
}

/// Backward compatibility facade for native_build_topology_graph.
pub fn native_build_topology_graph(discovery: Vec<NativeDiscoveryResult>) -> Vec<NativeEdge> {
    let identities: Vec<NativeIdentity> =
        discovery.into_iter().filter_map(|d| d.identity).collect();
    build_topology_edges(&identities)
}
