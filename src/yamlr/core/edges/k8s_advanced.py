#!/usr/bin/env python3
"""
Yamlr K8S ADVANCED EDGES
------------------------
Complex Kubernetes resource relationships (EPIC-23 Phase 2).
"""

from __future__ import annotations

from yamlr.core.edges.base import AddEdgeFn, MakeKeyFn
from yamlr.core.edges.catalog import ResourceCatalog
from yamlr.core.graph_models import EdgeType, GraphEdge

__all__ = [
    "build_network_policy_edges",
    "build_pdb_edges",
    "build_priority_class_edges",
    "build_runtime_class_edges",
    "build_crd_instance_edges",
    "build_gateway_route_edges",
    "build_owner_edges",
    "build_volume_mount_edges",
    "build_namespace_edges",
    "build_endpoint_slice_edges",
    "build_vpa_edges",
    "build_gateway_class_edges",
    "build_kms_edges",
]


def build_network_policy_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """NetworkPolicy.podSelector → Workload.labels (NETPOL_MATCH) - Optimized."""
    policies = catalog.get_by_kind("NetworkPolicy")

    for policy in policies:
        if not policy.selector:
            continue
        pol_key = make_key("NetworkPolicy", policy)
        pol_ns = policy.namespace or "default"

        matches = catalog.find_matching_workloads(pol_ns, policy.selector)
        for wl in matches:
            wl_key = make_key(wl.kind, wl)
            add_edge(
                GraphEdge(
                    source_key=pol_key,
                    target_key=wl_key,
                    edge_type=EdgeType.NETPOL_MATCH,
                )
            )


def build_pdb_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """PDB.selector → Workload.labels (PDB_MATCH) - Optimized."""
    pdbs = catalog.get_by_kind("PodDisruptionBudget")

    for pdb in pdbs:
        if not pdb.selector:
            continue
        pdb_key = make_key("PodDisruptionBudget", pdb)
        pdb_ns = pdb.namespace or "default"

        matches = catalog.find_matching_workloads(pdb_ns, pdb.selector)
        for wl in matches:
            wl_key = make_key(wl.kind, wl)
            add_edge(
                GraphEdge(
                    source_key=pdb_key,
                    target_key=wl_key,
                    edge_type=EdgeType.PDB_MATCH,
                )
            )


def build_priority_class_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Pod.priorityClassName → PriorityClass.name (PRIORITY_CLASS)."""
    workloads = [
        i
        for i in catalog.identities
        if getattr(i, "priority_class_name", None)
        and i.kind in ("Deployment", "StatefulSet", "DaemonSet", "Pod", "Job", "CronJob")
    ]

    for wl in workloads:
        pc = catalog.get_by_key("PriorityClass", "default", wl.priority_class_name)
        if pc:
            add_edge(
                GraphEdge(
                    source_key=make_key(wl.kind, wl),
                    target_key=make_key("PriorityClass", pc),
                    edge_type=EdgeType.PRIORITY_CLASS,
                )
            )


def build_runtime_class_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Pod.runtimeClassName → RuntimeClass.name (RUNTIME_CLASS)."""
    workloads = [
        i
        for i in catalog.identities
        if getattr(i, "runtime_class_name", None)
        and i.kind in ("Deployment", "StatefulSet", "DaemonSet", "Pod", "Job", "CronJob")
    ]

    for wl in workloads:
        rc = catalog.get_by_key("RuntimeClass", "default", wl.runtime_class_name)
        if rc:
            add_edge(
                GraphEdge(
                    source_key=make_key(wl.kind, wl),
                    target_key=make_key("RuntimeClass", rc),
                    edge_type=EdgeType.RUNTIME_CLASS,
                )
            )


def build_crd_instance_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """CustomResource.apiVersion group → CRD.group (CRD_INSTANCE)."""
    crds = catalog.get_by_kind("CustomResourceDefinition")
    custom_resources = [i for i in catalog.identities if getattr(i, "crd_group", None)]

    for cr in custom_resources:
        for crd in crds:
            if crd.name and crd.name.endswith(f".{cr.crd_group}"):
                add_edge(
                    GraphEdge(
                        source_key=make_key(cr.kind, cr),
                        target_key=make_key("CustomResourceDefinition", crd),
                        edge_type=EdgeType.CRD_INSTANCE,
                        metadata={"group": cr.crd_group},
                    )
                )


def build_gateway_route_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """HTTPRoute.backendRefs[].service → Service.name (GATEWAY_ROUTE)."""
    routes = [i for i in catalog.identities if i.kind == "HTTPRoute" and getattr(i, "gateway_route_backends", None)]

    for route in routes:
        route_key = make_key("HTTPRoute", route)
        route_ns = route.namespace or "default"
        for backend in route.gateway_route_backends:
            svc_name = backend.get("service", "")
            if svc_name:
                svc = catalog.get_by_key("Service", route_ns, svc_name)
                if svc:
                    add_edge(
                        GraphEdge(
                            source_key=route_key,
                            target_key=make_key("Service", svc),
                            edge_type=EdgeType.GATEWAY_ROUTE,
                            metadata={"port": backend.get("port", "")},
                        )
                    )


def build_owner_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Resource.ownerReferences[] → Owner Resource (OWNER_REF)."""
    for ident in catalog.identities:
        if not ident.owner_refs:
            continue

        source_key = make_key(ident.kind, ident)
        ns = ident.namespace or "default"
        for owner in ident.owner_refs:
            o_kind = owner.get("kind")
            o_name = owner.get("name")

            if o_kind and o_name:
                # Owner can be same NS or Cluster-scoped
                target = catalog.get_by_key(o_kind, ns, o_name) or catalog.get_by_key(o_kind, "default", o_name)
                if target:
                    add_edge(
                        GraphEdge(
                            source_key=source_key,
                            target_key=make_key(target.kind, target),
                            edge_type=EdgeType.OWNER_REF,
                        )
                    )


def build_volume_mount_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Container.volumeMounts[].name → Pod.volumes[].name (VOLUME_MOUNT)."""
    for ident in catalog.identities:
        if not ident.volume_mounts:
            continue

        source_key = make_key(ident.kind, ident)
        for mount in ident.volume_mounts:
            m_name = mount.get("name")
            if m_name:
                add_edge(
                    GraphEdge(
                        source_key=source_key,
                        target_key=source_key,
                        edge_type=EdgeType.VOLUME_MOUNT,
                        metadata={"mount": m_name, "path": mount.get("path")},
                    )
                )


def build_namespace_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Resource.namespace → Namespace.name (NAMESPACE_QUOTA)."""
    for ident in catalog.identities:
        if ident.kind == "Namespace":
            continue

        ns_name = ident.namespace or "default"
        ns_obj = catalog.get_by_key("Namespace", "default", ns_name)
        if ns_obj:
            add_edge(
                GraphEdge(
                    source_key=make_key(ident.kind, ident),
                    target_key=make_key("Namespace", ns_obj),
                    edge_type=EdgeType.NAMESPACE_QUOTA,
                )
            )


def build_endpoint_slice_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Service → EndpointSlice (ENDPOINT_SLICE)."""
    slices = catalog.get_by_kind("EndpointSlice")
    for ident in slices:
        if ident.labels:
            svc_name = ident.labels.get("kubernetes.io/service-name")
            ns = ident.namespace or "default"
            if svc_name:
                svc = catalog.get_by_key("Service", ns, svc_name)
                if svc:
                    add_edge(
                        GraphEdge(
                            source_key=make_key("Service", svc),
                            target_key=make_key("EndpointSlice", ident),
                            edge_type=EdgeType.ENDPOINT_SLICE,
                        )
                    )


def build_vpa_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """VPA → Workload (VPA_TARGET)."""
    vpas = catalog.get_by_kind("VerticalPodAutoscaler")

    for ident in vpas:
        if ident.vpa_target:
            t_kind = ident.vpa_target.get("kind")
            t_name = ident.vpa_target.get("name")
            ns = ident.namespace or "default"
            if t_kind and t_name:
                target = catalog.get_by_key(t_kind, ns, t_name)
                if target:
                    add_edge(
                        GraphEdge(
                            source_key=make_key("VerticalPodAutoscaler", ident),
                            target_key=make_key(target.kind, target),
                            edge_type=EdgeType.VPA_TARGET,
                        )
                    )


def build_gateway_class_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Gateway → GatewayClass (GATEWAY_CLASS)."""
    gateways = catalog.get_by_kind("Gateway")
    for ident in gateways:
        if ident.gateway_class_ref:
            gc = catalog.get_by_key("GatewayClass", "default", ident.gateway_class_ref)
            if gc:
                add_edge(
                    GraphEdge(
                        source_key=make_key("Gateway", ident),
                        target_key=make_key("GatewayClass", gc),
                        edge_type=EdgeType.GATEWAY_CLASS,
                    )
                )


def build_kms_edges(
    catalog: ResourceCatalog,
    add_edge: AddEdgeFn,
    make_key: MakeKeyFn,
) -> None:
    """Resource → KMS Key (KMS_LINK)."""
    for ident in catalog.identities:
        if ident.kms_key_refs:
            source_key = make_key(ident.kind, ident)
            for key_id in ident.kms_key_refs:
                add_edge(
                    GraphEdge(
                        source_key=source_key,
                        target_key=f"KMSKey/{key_id}",
                        edge_type=EdgeType.KMS_LINK,
                        metadata={"key_id": key_id},
                    )
                )
