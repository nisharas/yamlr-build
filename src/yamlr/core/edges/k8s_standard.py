#!/usr/bin/env python3
"""
Yamlr K8S STANDARD EDGES
------------------------
Core Kubernetes resource relationships.
"""

from yamlr.core.edges.base import AddEdgeFn, MakeKeyFn
from yamlr.core.edges.catalog import ResourceCatalog
from yamlr.core.graph_models import EdgeType, GraphEdge
from yamlr.models import WORKLOAD_KINDS

__all__ = [
    "build_selector_edges",
    "build_port_edges",
    "build_ingress_edges",
    "build_config_edges",
    "build_secret_edges",
    "build_pvc_edges",
    "build_hpa_edges",
    "build_rbac_edges",
    "build_service_account_edges",
    "build_storage_class_edges",
    "build_ingress_class_edges",
]


def build_selector_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Service.selector → Workload.labels (SELECTOR_MATCH) - Optimized O(N)."""
    services = catalog.get_by_kind("Service")

    for svc in services:
        if not svc.selector:
            continue

        svc_ns = svc.namespace or "default"
        svc_key = make_key("Service", svc)

        matches = catalog.find_matching_workloads(svc_ns, svc.selector)

        for wl in matches:
            wl_key = make_key(wl.kind, wl)
            add_edge(
                GraphEdge(
                    source_key=svc_key,
                    target_key=wl_key,
                    edge_type=EdgeType.SELECTOR_MATCH,
                )
            )


def build_port_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Service.ports[].targetPort → Container.ports[] (PORT_BIND) - Optimized O(P)."""
    services = catalog.get_by_kind("Service")

    for svc in services:
        if not svc.service_ports:
            continue

        svc_key = make_key("Service", svc)
        for sp in svc.service_ports:
            target_port = str(sp.get("targetPort", ""))
            if not target_port:
                continue

            workloads = catalog.get_workloads_by_port(target_port)
            for wl in workloads:
                # Ports must be in the same namespace or globally accessible?
                # Usually Service targets Pods in same Namespace.
                if (wl.namespace or "default") != (svc.namespace or "default"):
                    continue

                wl_key = make_key(wl.kind, wl)
                add_edge(
                    GraphEdge(
                        source_key=svc_key,
                        target_key=wl_key,
                        edge_type=EdgeType.PORT_BIND,
                        metadata={"port": target_port},
                    )
                )


def build_ingress_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Ingress.backends[].service → Service.name (INGRESS_BACKEND) - Optimized O(I)."""
    ingresses = catalog.get_by_kind("Ingress")

    for ing in ingresses:
        ing_key = make_key("Ingress", ing)
        ing_ns = ing.namespace or "default"
        for backend in ing.ingress_backends:
            svc_name = backend.get("service", "")
            if not svc_name:
                continue

            svc = catalog.get_by_key("Service", ing_ns, svc_name)
            if svc:
                svc_key = make_key("Service", svc)
                add_edge(
                    GraphEdge(
                        source_key=ing_key,
                        target_key=svc_key,
                        edge_type=EdgeType.INGRESS_BACKEND,
                        metadata={"port": backend.get("port", "")},
                    )
                )


def build_config_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Workload.config_refs[] → ConfigMap.name (CONFIG_REF)."""
    # Build list of all identities that have config_refs
    workloads = [i for i in catalog.identities if i.config_refs]

    for wl in workloads:
        wl_key = make_key(wl.kind, wl)
        wl_ns = wl.namespace or "default"
        for ref in wl.config_refs:
            cm = catalog.get_by_key("ConfigMap", wl_ns, ref)
            if cm:
                add_edge(
                    GraphEdge(
                        source_key=wl_key,
                        target_key=make_key("ConfigMap", cm),
                        edge_type=EdgeType.CONFIG_REF,
                    )
                )


def build_secret_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Workload.secret_refs[] → Secret.name (SECRET_REF)."""
    workloads = [i for i in catalog.identities if i.secret_refs or i.secret_volume_refs]

    for wl in workloads:
        wl_key = make_key(wl.kind, wl)
        wl_ns = wl.namespace or "default"
        all_refs = list(set(wl.secret_refs + wl.secret_volume_refs))
        for ref in all_refs:
            secret = catalog.get_by_key("Secret", wl_ns, ref)
            if secret:
                add_edge(
                    GraphEdge(
                        source_key=wl_key,
                        target_key=make_key("Secret", secret),
                        edge_type=EdgeType.SECRET_REF,
                    )
                )


def build_pvc_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Workload.volume_refs[] → PVC.name (PVC_REF)."""
    workloads = [i for i in catalog.identities if i.volume_refs]

    for wl in workloads:
        wl_key = make_key(wl.kind, wl)
        wl_ns = wl.namespace or "default"
        for ref in wl.volume_refs:
            pvc = catalog.get_by_key("PersistentVolumeClaim", wl_ns, ref)
            if pvc:
                add_edge(
                    GraphEdge(
                        source_key=wl_key,
                        target_key=make_key("PersistentVolumeClaim", pvc),
                        edge_type=EdgeType.PVC_REF,
                    )
                )


def build_hpa_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """HPA.scale_target → Workload.name (HPA_TARGET)."""
    hpas = catalog.get_by_kind("HorizontalPodAutoscaler")

    for hpa in hpas:
        if not hpa.scale_target:
            continue
        hpa_key = make_key("HorizontalPodAutoscaler", hpa)
        hpa_ns = hpa.namespace or "default"

        # Check standard workload kinds
        for kind in ("Deployment", "StatefulSet", "ReplicaSet"):
            wl = catalog.get_by_key(kind, hpa_ns, hpa.scale_target)
            if wl:
                add_edge(
                    GraphEdge(
                        source_key=hpa_key,
                        target_key=make_key(wl.kind, wl),
                        edge_type=EdgeType.HPA_TARGET,
                    )
                )
                break


def build_rbac_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """RoleBinding.role_refs[] → Role/ClusterRole (RBAC_BINDING)."""
    bindings = catalog.get_by_kind("RoleBinding") + catalog.get_by_kind("ClusterRoleBinding")

    for binding in bindings:
        b_key = make_key(binding.kind, binding)
        b_ns = binding.namespace or "default"
        all_refs = list(set(binding.role_refs + binding.cluster_role_refs))
        for ref in all_refs:
            # RBAC is tricky: Role is NS-scoped, ClusterRole is Global
            role = catalog.get_by_key("Role", b_ns, ref) or catalog.get_by_key(
                "ClusterRole", "default", ref
            )  # ClusterRole doesn't have NS, using default as index key

            if role:
                add_edge(
                    GraphEdge(
                        source_key=b_key,
                        target_key=make_key(role.kind, role),
                        edge_type=EdgeType.RBAC_BINDING,
                    )
                )


def build_service_account_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Pod.service_account → ServiceAccount.name (SERVICE_ACCOUNT)."""
    workloads = []
    for k in WORKLOAD_KINDS:
        workloads.extend(catalog.get_by_kind(k))

    for wl in workloads:
        if not wl.service_account:
            continue
        wl_ns = wl.namespace or "default"
        sa = catalog.get_by_key("ServiceAccount", wl_ns, wl.service_account)
        if sa:
            add_edge(
                GraphEdge(
                    source_key=make_key(wl.kind, wl),
                    target_key=make_key("ServiceAccount", sa),
                    edge_type=EdgeType.SERVICE_ACCOUNT,
                )
            )


def build_storage_class_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """PVC.storage_class_refs[] → StorageClass.name (STORAGE_CLASS)."""
    pvcs = [i for i in catalog.identities if i.storage_class_refs]

    for pvc in pvcs:
        pvc_key = make_key(pvc.kind, pvc)
        for ref in pvc.storage_class_refs:
            sc = catalog.get_by_key("StorageClass", "default", ref)  # Cluster scoped
            if sc:
                add_edge(
                    GraphEdge(
                        source_key=pvc_key,
                        target_key=make_key("StorageClass", sc),
                        edge_type=EdgeType.STORAGE_CLASS,
                    )
                )


def build_ingress_class_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Ingress.ingress_class_refs[] → IngressClass.name (INGRESS_CLASS)."""
    ingresses = [i for i in catalog.identities if i.ingress_class_refs]

    for ing in ingresses:
        ing_key = make_key(ing.kind, ing)
        for ref in ing.ingress_class_refs:
            ic = catalog.get_by_key("IngressClass", "default", ref)  # Cluster scoped
            if ic:
                add_edge(
                    GraphEdge(
                        source_key=ing_key,
                        target_key=make_key("IngressClass", ic),
                        edge_type=EdgeType.INGRESS_CLASS,
                    )
                )
