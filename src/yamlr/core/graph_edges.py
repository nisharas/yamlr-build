#!/usr/bin/env python3
"""
Yamlr GRAPH EDGE BUILDERS
----------------------------
Functions that construct typed edges between Kubernetes resources.

Why: Extracted from ResourceGraph to maintain <500 line module limit.
     Each builder is a pure function: takes identities, returns edges.
     This separation enables testing edge logic independently from
     graph traversal.

Architecture:
    - Pure functions (no I/O, no side-effects).
    - Each function receives a list of ManifestIdentity objects and
      an add_edge callback.
    - Edge builders are called by ResourceGraph.build() in sequence.

Gate Compliance:
    - Trust: Detection-only (no mutations to identities).
    - Determinism: Same identities → same edges.
    - Speed: O(N²) worst-case per builder; acceptable for <1000 resources.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-28
"""

from typing import Callable, Dict, List, Optional

from yamlr.models import ManifestIdentity
from yamlr.core.resource_graph import EdgeType, GraphEdge


# Type alias for the edge registration callback
AddEdgeFn = Callable[[GraphEdge], None]
MakeKeyFn = Callable[[str, ManifestIdentity], str]


def labels_match(
    selector: Optional[Dict[str, str]], labels: Optional[Dict[str, str]]
) -> bool:
    """Check if a selector matches a set of labels.

    Why: Replicates Kubernetes selector semantics — all selector
         keys must exist in labels with matching values.
    """
    if not selector or not labels:
        return False
    return all(labels.get(k) == v for k, v in selector.items())


# =====================================================================
# ORIGINAL EDGE BUILDERS (11 types)
# =====================================================================


def build_selector_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Service.selector → Workload.labels (SELECTOR_MATCH).

    Why: Most common K8s relationship. Broken selector = traffic blackhole.
    """
    services = [i for i in identities if i.kind == "Service" and i.selector]
    workloads = [
        i for i in identities
        if i.kind in ("Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Pod")
        and i.labels
    ]

    for svc in services:
        svc_key = make_key("Service", svc)
        for wl in workloads:
            if labels_match(svc.selector, wl.labels):
                wl_key = make_key(wl.kind, wl)
                add_edge(GraphEdge(
                    source_key=svc_key, target_key=wl_key,
                    edge_type=EdgeType.SELECTOR_MATCH,
                ))


def build_port_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Service.ports[].targetPort → Container.ports[] (PORT_BIND).

    Why: Port mismatches are silent failures — high-risk, hard to debug.
    """
    services = [i for i in identities if i.kind == "Service" and i.service_ports]
    workloads = [
        i for i in identities
        if i.kind in ("Deployment", "StatefulSet", "DaemonSet", "Pod")
        and i.container_ports
    ]

    for svc in services:
        svc_key = make_key("Service", svc)
        for wl in workloads:
            wl_key = make_key(wl.kind, wl)
            for sp in svc.service_ports:
                target_port = str(sp.get("targetPort", ""))
                if target_port and target_port in wl.container_ports:
                    add_edge(GraphEdge(
                        source_key=svc_key, target_key=wl_key,
                        edge_type=EdgeType.PORT_BIND,
                        metadata={"port": target_port},
                    ))


def build_ingress_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Ingress.backends[].service → Service.name (INGRESS_BACKEND).

    Why: Ingress is traffic-facing. Broken edge = external users blocked.
    """
    ingresses = [i for i in identities if i.kind == "Ingress" and i.ingress_backends]
    services = {i.name: i for i in identities if i.kind == "Service" and i.name}

    for ing in ingresses:
        ing_key = make_key("Ingress", ing)
        for backend in ing.ingress_backends:
            svc_name = backend.get("service", "")
            if svc_name and svc_name in services:
                svc = services[svc_name]
                svc_key = make_key("Service", svc)
                add_edge(GraphEdge(
                    source_key=ing_key, target_key=svc_key,
                    edge_type=EdgeType.INGRESS_BACKEND,
                    metadata={"port": backend.get("port", "")},
                ))


def build_config_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Workload.config_refs[] → ConfigMap.name (CONFIG_REF).

    Why: Missing ConfigMap = crash-loop. Data dependency, medium-to-high risk.
    """
    configs = {i.name: i for i in identities if i.kind == "ConfigMap" and i.name}
    workloads = [i for i in identities if i.config_refs]

    for wl in workloads:
        wl_key = make_key(wl.kind, wl)
        for ref in wl.config_refs:
            if ref in configs:
                cm = configs[ref]
                add_edge(GraphEdge(
                    source_key=wl_key, target_key=make_key("ConfigMap", cm),
                    edge_type=EdgeType.CONFIG_REF,
                ))


def build_secret_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Workload.secret_refs[] → Secret.name (SECRET_REF).

    Why: Missing secrets = Pod failure + security implications.
    """
    secrets = {i.name: i for i in identities if i.kind == "Secret" and i.name}
    workloads = [i for i in identities if i.secret_refs or i.secret_volume_refs]

    for wl in workloads:
        wl_key = make_key(wl.kind, wl)
        all_refs = list(set(wl.secret_refs + wl.secret_volume_refs))
        for ref in all_refs:
            if ref in secrets:
                add_edge(GraphEdge(
                    source_key=wl_key, target_key=make_key("Secret", secrets[ref]),
                    edge_type=EdgeType.SECRET_REF,
                ))


def build_pvc_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Workload.volume_refs[] → PVC.name (PVC_REF).

    Why: Missing PVC = Pod scheduling failure. High operational risk.
    """
    pvcs = {
        i.name: i for i in identities
        if i.kind == "PersistentVolumeClaim" and i.name
    }
    workloads = [i for i in identities if i.volume_refs]

    for wl in workloads:
        wl_key = make_key(wl.kind, wl)
        for ref in wl.volume_refs:
            if ref in pvcs:
                add_edge(GraphEdge(
                    source_key=wl_key,
                    target_key=make_key("PersistentVolumeClaim", pvcs[ref]),
                    edge_type=EdgeType.PVC_REF,
                ))


def build_hpa_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """HPA.scale_target → Workload.name (HPA_TARGET).

    Why: HPA targeting non-existent Deployment = autoscaling silently fails.
    """
    hpas = [
        i for i in identities
        if i.kind == "HorizontalPodAutoscaler" and i.scale_target
    ]
    workloads = {
        i.name: i for i in identities
        if i.kind in ("Deployment", "StatefulSet", "ReplicaSet") and i.name
    }

    for hpa in hpas:
        hpa_key = make_key("HorizontalPodAutoscaler", hpa)
        if hpa.scale_target in workloads:
            wl = workloads[hpa.scale_target]
            add_edge(GraphEdge(
                source_key=hpa_key, target_key=make_key(wl.kind, wl),
                edge_type=EdgeType.HPA_TARGET,
            ))


def build_rbac_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """RoleBinding.role_refs[] → Role/ClusterRole (RBAC_BINDING).

    Why: Broken RBAC = silent permission failures.
    """
    roles = {i.name: i for i in identities if i.kind in ("Role", "ClusterRole") and i.name}
    bindings = [
        i for i in identities
        if i.kind in ("RoleBinding", "ClusterRoleBinding")
        and (i.role_refs or i.cluster_role_refs)
    ]

    for binding in bindings:
        b_key = make_key(binding.kind, binding)
        all_refs = list(set(binding.role_refs + binding.cluster_role_refs))
        for ref in all_refs:
            if ref in roles:
                role = roles[ref]
                add_edge(GraphEdge(
                    source_key=b_key, target_key=make_key(role.kind, role),
                    edge_type=EdgeType.RBAC_BINDING,
                ))


def build_service_account_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Pod.service_account → ServiceAccount.name (SERVICE_ACCOUNT).

    Why: Missing SA prevents Pod scheduling in RBAC-enforced clusters.
    """
    sa_index = {
        i.name: i for i in identities if i.kind == "ServiceAccount" and i.name
    }
    workloads = [
        i for i in identities
        if i.service_account and i.kind in (
            "Deployment", "StatefulSet", "DaemonSet", "Pod", "Job", "CronJob"
        )
    ]

    for wl in workloads:
        if wl.service_account in sa_index:
            sa = sa_index[wl.service_account]
            add_edge(GraphEdge(
                source_key=make_key(wl.kind, wl),
                target_key=make_key("ServiceAccount", sa),
                edge_type=EdgeType.SERVICE_ACCOUNT,
            ))


def build_storage_class_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """PVC.storage_class_refs[] → StorageClass.name (STORAGE_CLASS).

    Why: PVC binding fails silently if StorageClass doesn't exist.
    """
    sc_index = {
        i.name: i for i in identities if i.kind == "StorageClass" and i.name
    }
    pvcs = [i for i in identities if i.storage_class_refs]

    for pvc in pvcs:
        pvc_key = make_key(pvc.kind, pvc)
        for ref in pvc.storage_class_refs:
            if ref in sc_index:
                add_edge(GraphEdge(
                    source_key=pvc_key,
                    target_key=make_key("StorageClass", sc_index[ref]),
                    edge_type=EdgeType.STORAGE_CLASS,
                ))


def build_ingress_class_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Ingress.ingress_class_refs[] → IngressClass.name (INGRESS_CLASS).

    Why: Ingress without valid IngressClass is ignored — traffic drops.
    """
    ic_index = {
        i.name: i for i in identities if i.kind == "IngressClass" and i.name
    }
    ingresses = [i for i in identities if i.ingress_class_refs]

    for ing in ingresses:
        ing_key = make_key(ing.kind, ing)
        for ref in ing.ingress_class_refs:
            if ref in ic_index:
                add_edge(GraphEdge(
                    source_key=ing_key,
                    target_key=make_key("IngressClass", ic_index[ref]),
                    edge_type=EdgeType.INGRESS_CLASS,
                ))


# =====================================================================
# NEW EDGE BUILDERS (6 types — EPIC-23 Phase 2)
# =====================================================================


def build_network_policy_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """NetworkPolicy.podSelector → Workload.labels (NETWORK_POLICY_TARGET).

    Why: Broken NetworkPolicy selector = pods run unprotected (security hole)
         OR pods are blocked from all traffic (availability failure).
         Both failure modes are silent until production impact.
    """
    policies = [
        i for i in identities
        if i.kind == "NetworkPolicy" and i.selector
    ]
    workloads = [
        i for i in identities
        if i.kind in ("Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Pod")
        and i.labels
    ]

    for policy in policies:
        pol_key = make_key("NetworkPolicy", policy)
        for wl in workloads:
            if labels_match(policy.selector, wl.labels):
                wl_key = make_key(wl.kind, wl)
                add_edge(GraphEdge(
                    source_key=pol_key, target_key=wl_key,
                    edge_type=EdgeType.NETWORK_POLICY_TARGET,
                ))


def build_pdb_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """PDB.selector → Workload.labels (PDB_TARGET).

    Why: Broken PDB selector = no disruption protection during node
         drains, upgrades, or voluntary evictions. Critical for
         production availability guarantees.
    """
    pdbs = [
        i for i in identities
        if i.kind == "PodDisruptionBudget" and i.selector
    ]
    workloads = [
        i for i in identities
        if i.kind in ("Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Pod")
        and i.labels
    ]

    for pdb in pdbs:
        pdb_key = make_key("PodDisruptionBudget", pdb)
        for wl in workloads:
            if labels_match(pdb.selector, wl.labels):
                wl_key = make_key(wl.kind, wl)
                add_edge(GraphEdge(
                    source_key=pdb_key, target_key=wl_key,
                    edge_type=EdgeType.PDB_TARGET,
                ))


def build_priority_class_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Pod.priorityClassName → PriorityClass.name (PRIORITY_CLASS).

    Why: Missing PriorityClass causes scheduling anomalies and
         unexpected Pod preemption behavior. Cluster-scoped resource.
    """
    pc_index = {
        i.name: i for i in identities
        if i.kind == "PriorityClass" and i.name
    }
    workloads = [
        i for i in identities
        if getattr(i, "priority_class_name", None)
        and i.kind in ("Deployment", "StatefulSet", "DaemonSet", "Pod", "Job", "CronJob")
    ]

    for wl in workloads:
        if wl.priority_class_name in pc_index:
            pc = pc_index[wl.priority_class_name]
            add_edge(GraphEdge(
                source_key=make_key(wl.kind, wl),
                target_key=make_key("PriorityClass", pc),
                edge_type=EdgeType.PRIORITY_CLASS,
            ))


def build_runtime_class_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Pod.runtimeClassName → RuntimeClass.name (RUNTIME_CLASS).

    Why: Missing RuntimeClass = Pod stuck in Pending forever.
         Silent scheduling failure with no error in Pod events.
    """
    rc_index = {
        i.name: i for i in identities
        if i.kind == "RuntimeClass" and i.name
    }
    workloads = [
        i for i in identities
        if getattr(i, "runtime_class_name", None)
        and i.kind in ("Deployment", "StatefulSet", "DaemonSet", "Pod", "Job", "CronJob")
    ]

    for wl in workloads:
        if wl.runtime_class_name in rc_index:
            rc = rc_index[wl.runtime_class_name]
            add_edge(GraphEdge(
                source_key=make_key(wl.kind, wl),
                target_key=make_key("RuntimeClass", rc),
                edge_type=EdgeType.RUNTIME_CLASS,
            ))


def build_crd_instance_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """CustomResource.apiVersion group → CRD.group (CRD_INSTANCE).

    Why: Custom resources without their CRD are silently ignored by
         the API server. The resource appears to apply but has no effect.
         This is one of the most confusing K8s failure modes.
    """
    crds = {
        i.name: i for i in identities
        if i.kind == "CustomResourceDefinition" and i.name
    }
    custom_resources = [
        i for i in identities
        if getattr(i, "crd_group", None)
    ]

    for cr in custom_resources:
        # Match CRD by group name extracted from apiVersion
        # Example: "monitoring.coreos.com/v1" → group = "monitoring.coreos.com"
        for crd_name, crd in crds.items():
            # CRD names follow pattern: <plural>.<group>
            # e.g., "prometheusrules.monitoring.coreos.com"
            if crd_name.endswith(f".{cr.crd_group}"):
                add_edge(GraphEdge(
                    source_key=make_key(cr.kind, cr),
                    target_key=make_key("CustomResourceDefinition", crd),
                    edge_type=EdgeType.CRD_INSTANCE,
                    metadata={"group": cr.crd_group},
                ))


def build_gateway_route_edges(
    identities: List[ManifestIdentity],
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """HTTPRoute.backendRefs[].service → Service.name (GATEWAY_ROUTE).

    Why: Gateway API is replacing Ingress in modern K8s clusters.
         HTTPRoute is the standard way to route traffic. Broken
         backend references = traffic loss (same risk as Ingress).
    """
    routes = [
        i for i in identities
        if i.kind == "HTTPRoute"
        and getattr(i, "gateway_route_backends", None)
    ]
    services = {i.name: i for i in identities if i.kind == "Service" and i.name}

    for route in routes:
        route_key = make_key("HTTPRoute", route)
        for backend in route.gateway_route_backends:
            svc_name = backend.get("service", "")
            if svc_name and svc_name in services:
                svc = services[svc_name]
                add_edge(GraphEdge(
                    source_key=route_key,
                    target_key=make_key("Service", svc),
                    edge_type=EdgeType.GATEWAY_ROUTE,
                    metadata={"port": backend.get("port", "")},
                ))


# =====================================================================
# BUILDER REGISTRY
# =====================================================================

# Ordered list of all edge builders. ResourceGraph.build() calls
# each in sequence. Adding a new builder = append here + add EdgeType.

ALL_EDGE_BUILDERS = [
    # Original 11
    build_selector_edges,
    build_port_edges,
    build_ingress_edges,
    build_config_edges,
    build_secret_edges,
    build_pvc_edges,
    build_hpa_edges,
    build_rbac_edges,
    build_service_account_edges,
    build_storage_class_edges,
    build_ingress_class_edges,
    # New 6 (EPIC-23 Phase 2)
    build_network_policy_edges,
    build_pdb_edges,
    build_priority_class_edges,
    build_runtime_class_edges,
    build_crd_instance_edges,
    build_gateway_route_edges,
]
