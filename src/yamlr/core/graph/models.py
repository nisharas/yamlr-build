#!/usr/bin/env python3
"""
Yamlr GRAPH MODELS
------------------
Fundamental data structures for the Resource Dependency Graph.

Why: Extracted from resource_graph.py to break circular dependencies
     with the modular edges package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict

from yamlr.models import ManifestIdentity

__all__ = ["EdgeType", "GraphNode", "GraphEdge"]


class EdgeType(Enum):
    """Typed relationship categories between Kubernetes resources."""

    # Original 11 (Phase 1)
    SELECTOR_MATCH = "selector_match"
    PORT_BIND = "port_bind"
    INGRESS_BACKEND = "ingress_backend"
    CONFIG_REF = "config_ref"
    SECRET_REF = "secret_ref"
    PVC_REF = "pvc_ref"
    HPA_TARGET = "hpa_target"
    RBAC_BINDING = "rbac_binding"
    SERVICE_ACCOUNT = "service_account"
    STORAGE_CLASS = "storage_class"
    INGRESS_CLASS = "ingress_class"
    SERVICE_REF = "service_ref"
    ROLE_REF = "role_ref"
    CLUSTER_ROLE_REF = "cluster_role_ref"
    SERVICE_ACCOUNT_REF = "service_account_ref"

    # New 6 (Phase 2 — EPIC-23)
    NETWORK_POLICY_TARGET = "network_policy_target"
    PDB_TARGET = "pdb_target"
    PRIORITY_CLASS = "priority_class"
    RUNTIME_CLASS = "runtime_class"
    CRD_INSTANCE = "crd_instance"
    GATEWAY_ROUTE = "gateway_route"

    # New 2 (Phase 3 — STRATEGIC EXPANSION)
    CLOUD_REF = "cloud_ref"
    CREDENTIAL_LINK = "credential_link"

    # Phase 8: Deep Dependency Coverage
    OWNER_REF = "owner_ref"
    VOLUME_MOUNT = "volume_mount"
    NAMESPACE_QUOTA = "namespace_quota"
    ENDPOINT_SLICE = "endpoint_slice"
    VPA_TARGET = "vpa_target"
    GATEWAY_CLASS = "gateway_class"
    KMS_LINK = "kms_link"


@dataclass(slots=True)
class GraphNode:
    """A single Kubernetes resource in the dependency graph."""

    kind: str
    namespace: str
    name: str
    identity: ManifestIdentity
    file_path: str = ""

    @property
    def key(self) -> str:
        """Unique node identifier: kind/namespace/name."""
        return f"{self.kind}/{self.namespace}/{self.name}"


@dataclass(slots=True)
class GraphEdge:
    """A typed directional relationship between two resources."""

    source_key: str
    target_key: str
    edge_type: EdgeType
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
