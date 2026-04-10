#!/usr/bin/env python3
"""
Yamlr CORE EDGES
----------------
Modular entry point for all graph edge building logic.
"""

from __future__ import annotations

from typing import Callable, List

from yamlr.core.edges.catalog import ResourceCatalog
from yamlr.core.graph_models import GraphEdge
from yamlr.models import ManifestIdentity

# Type aliases for edge construction
AddEdgeFn = Callable[[GraphEdge], None]
MakeKeyFn = Callable[[str, ManifestIdentity], str]
# New: Strategic Edge Building Function Signature
# def EdgeBuilder(catalog: ResourceCatalog, add_edge: AddEdgeFn, make_key: MakeKeyFn) -> None:

from yamlr.core.edges.cross_domain import (
    build_cross_domain_edges,
)
from yamlr.core.edges.k8s_advanced import (
    build_crd_instance_edges,
    build_endpoint_slice_edges,
    build_gateway_class_edges,
    build_gateway_route_edges,
    build_kms_edges,
    build_namespace_edges,
    build_network_policy_edges,
    build_owner_edges,
    build_pdb_edges,
    build_priority_class_edges,
    build_runtime_class_edges,
    build_volume_mount_edges,
    build_vpa_edges,
)
from yamlr.core.edges.k8s_standard import (
    build_config_edges,
    build_hpa_edges,
    build_ingress_class_edges,
    build_ingress_edges,
    build_port_edges,
    build_pvc_edges,
    build_rbac_edges,
    build_secret_edges,
    build_selector_edges,
    build_service_account_edges,
    build_storage_class_edges,
)

# Registry for ResourceGraph consumption
ALL_EDGE_BUILDERS = [
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
    build_network_policy_edges,
    build_pdb_edges,
    build_priority_class_edges,
    build_runtime_class_edges,
    build_crd_instance_edges,
    build_gateway_route_edges,
    build_owner_edges,
    build_volume_mount_edges,
    build_namespace_edges,
    build_endpoint_slice_edges,
    build_vpa_edges,
    build_gateway_class_edges,
    build_kms_edges,
    # New (Strategic Expansion)
    build_cross_domain_edges,
]
