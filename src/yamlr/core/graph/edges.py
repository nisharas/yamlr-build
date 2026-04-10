#!/usr/bin/env python3
"""
Yamlr GRAPH EDGE BUILDERS (Re-export)
-------------------------------------
Legacy entry point for edge building logic.

Why: Re-exports from yamlr.core.edges package to maintain backward
     compatibility while enforcing <500 line module limits.
"""

from __future__ import annotations

from yamlr.core.edges import (
    ALL_EDGE_BUILDERS,
    AddEdgeFn,
    MakeKeyFn,
)
from yamlr.core.edges.base import AddEdgeFn, MakeKeyFn, labels_match

__all__ = ["AddEdgeFn", "MakeKeyFn", "labels_match", "ALL_EDGE_BUILDERS"]

# Backward compatibility for specific builders if needed by legacy code
from yamlr.core.edges.k8s_advanced import (
    build_crd_instance_edges,
    build_gateway_route_edges,
    build_namespace_edges,
    build_network_policy_edges,
    build_owner_edges,
    build_pdb_edges,
    build_priority_class_edges,
    build_runtime_class_edges,
    build_volume_mount_edges,
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
