#!/usr/bin/env python3
"""
Yamlr RESOURCE DEPENDENCY GRAPH
---------------------------------
Builds a typed dependency graph from ManifestIdentity objects.
Enables blast-radius analysis, dependency traversal, and
system-level safety reasoning.

Why: Transforms Yamlr from file-level healing to system-level safety
     intelligence. The graph enables answering: "If this resource fails,
     what else is impacted?" — the core question for a Safety Engine.

Architecture:
    - Graph structure + public API + traversal live here.
    - Edge builder logic is in core/graph_edges.py (extracted per
      500-line modularity rule).
    - Does NOT replace CrossResourceAnalyzer or ReferenceResolver.
    - Existing detectors become data sources that feed graph edges.

Gate Compliance:
    - Trust: Detection-only (no side-effects on healing behavior).
    - Determinism: Same identities → same graph (sorted construction).
    - Speed: O(N²) worst-case for edge building; acceptable for <1000 resources.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-28
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.resource_graph")


class EdgeType(Enum):
    """Typed relationship categories between Kubernetes resources.

    Why: Explicit edge types enable precise traversal queries and
         risk classification (e.g., INGRESS_BACKEND = traffic-facing).

    Coverage: 17 edge types spanning traffic, data, scheduling,
              security, and CRD dependencies.
    """

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

    # New 6 (Phase 2 — EPIC-23)
    NETWORK_POLICY_TARGET = "network_policy_target"
    PDB_TARGET = "pdb_target"
    PRIORITY_CLASS = "priority_class"
    RUNTIME_CLASS = "runtime_class"
    CRD_INSTANCE = "crd_instance"
    GATEWAY_ROUTE = "gateway_route"


@dataclass(slots=True)
class GraphNode:
    """A single Kubernetes resource in the dependency graph.

    Why: Nodes carry identity metadata so traversal results are
         immediately actionable without re-querying the original data.
    """

    kind: str
    namespace: str
    name: str
    identity: ManifestIdentity
    file_path: str = ""

    @property
    def key(self) -> str:
        """Unique node identifier: kind/namespace/name.

        Why: Consistent key format enables O(1) lookups and
             deterministic graph construction regardless of input order.
        """
        return f"{self.kind}/{self.namespace}/{self.name}"


@dataclass(slots=True)
class GraphEdge:
    """A typed directional relationship between two resources.

    Why: Edges carry type and confidence metadata to support
         risk classification heuristics (e.g., fuzzy matches get
         lower confidence than exact references).
    """

    source_key: str
    target_key: str
    edge_type: EdgeType
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlastRadius:
    """Impact assessment for a single resource node.

    Why: Quantifies the downstream impact of a misconfiguration.
         Enterprise buyers need "scope of impact" for risk decisions.
    """

    source_key: str
    affected_nodes: List[GraphNode] = field(default_factory=list)
    depth: int = 0
    has_ingress_impact: bool = False
    has_data_impact: bool = False
    risk_level: str = "LOW"

    def to_dict(self) -> dict:
        """Serialize for JSON/SARIF export.

        Why: SARIF relatedLocations requires structured data for
             GitHub Advanced Security integration.
        """
        return {
            "source": self.source_key,
            "affected_count": len(self.affected_nodes),
            "affected_resources": [n.key for n in self.affected_nodes],
            "depth": self.depth,
            "has_ingress_impact": self.has_ingress_impact,
            "has_data_impact": self.has_data_impact,
            "risk_level": self.risk_level,
        }


class ResourceGraph:
    """Kubernetes resource dependency graph with 17 typed edge categories.

    Why: The dependency graph is the architectural foundation for
         Yamlr's Safety Engine identity. It enables system-level
         reasoning rather than per-file analysis.

    Usage:
        graph = ResourceGraph()
        graph.build(identities)
        radius = graph.blast_radius("Service/default/my-svc")
        print(f"Impact: {radius.risk_level}, {len(radius.affected_nodes)} affected")
    """

    def __init__(self) -> None:
        """Initialize empty graph structures.

        Why: Lazy construction allows the graph to be created once
             and populated when identities become available in the pipeline.
        """
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._outgoing: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._incoming: Dict[str, List[GraphEdge]] = defaultdict(list)

    # =====================================================================
    # PUBLIC API
    # =====================================================================

    def build(self, identities: List[ManifestIdentity]) -> None:
        """Construct the graph from a list of ManifestIdentity objects.

        Why: Single entry-point for graph construction ensures deterministic
             ordering. Identities are produced by Stage 3 of the pipeline.

        Args:
            identities: List of ManifestIdentity objects from scanner output.
        """
        # Lazy import to avoid circular dependency
        from yamlr.core.graph_edges import ALL_EDGE_BUILDERS

        self._nodes.clear()
        self._edges.clear()
        self._outgoing.clear()
        self._incoming.clear()

        # Phase 1: Index all resources as nodes
        for identity in identities:
            if not identity.kind or not identity.name:
                continue
            namespace = identity.namespace or "default"
            node = GraphNode(
                kind=identity.kind,
                namespace=namespace,
                name=identity.name,
                identity=identity,
            )
            self._nodes[node.key] = node

        # Phase 2: Build all typed edges via registry
        for builder in ALL_EDGE_BUILDERS:
            builder(identities, self._add_edge, self._make_key)

        logger.debug(
            f"Graph built: {len(self._nodes)} nodes, {len(self._edges)} edges"
        )

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return len(self._edges)

    def get_node(self, key: str) -> Optional[GraphNode]:
        """Retrieve a node by its key.

        Why: Direct key-based access for pipeline stages that already
             know the resource they're analyzing.
        """
        return self._nodes.get(key)

    def get_all_nodes(self) -> List[GraphNode]:
        """Return all nodes in deterministic order.

        Why: Determinism gate — sorted output ensures reproducible
             analysis across runs.
        """
        return sorted(self._nodes.values(), key=lambda n: n.key)

    def dependents(self, node_key: str) -> List[GraphNode]:
        """Resources that depend ON this node (downstream consumers).

        Why: Answers "What breaks if this resource is misconfigured?"
             Used by blast_radius calculation.

        Args:
            node_key: The resource key (kind/namespace/name).

        Returns:
            List of downstream dependent GraphNode objects.
        """
        result: List[GraphNode] = []
        for edge in self._incoming.get(node_key, []):
            source_node = self._nodes.get(edge.source_key)
            if source_node:
                result.append(source_node)
        return result

    def dependencies(self, node_key: str) -> List[GraphNode]:
        """Resources that this node depends on (upstream providers).

        Why: Answers "What does this resource need to function?"
             Used for pre-deployment validation.

        Args:
            node_key: The resource key (kind/namespace/name).

        Returns:
            List of upstream dependency GraphNode objects.
        """
        result: List[GraphNode] = []
        for edge in self._outgoing.get(node_key, []):
            target_node = self._nodes.get(edge.target_key)
            if target_node:
                result.append(target_node)
        return result

    def blast_radius(self, node_key: str) -> BlastRadius:
        """Calculate the full downstream impact of a resource failure.

        Why: THE core Safety Engine question. "If this Deployment fails,
             what else is impacted?" This is the category-defining feature.

        Algorithm: BFS traversal from the node, collecting all reachable
                   downstream nodes via incoming edges (dependents).

        Args:
            node_key: The resource key to analyze.

        Returns:
            BlastRadius with affected nodes, depth, and risk level.
        """
        radius = BlastRadius(source_key=node_key)

        if node_key not in self._nodes:
            return radius

        visited: Set[str] = {node_key}
        queue: List[Tuple[str, int]] = [(node_key, 0)]
        max_depth = 0

        while queue:
            current_key, depth = queue.pop(0)
            max_depth = max(max_depth, depth)

            for edge in self._incoming.get(current_key, []):
                if edge.source_key not in visited:
                    visited.add(edge.source_key)
                    source_node = self._nodes.get(edge.source_key)
                    if source_node:
                        radius.affected_nodes.append(source_node)
                        queue.append((edge.source_key, depth + 1))

            for edge in self._outgoing.get(current_key, []):
                if edge.target_key not in visited:
                    visited.add(edge.target_key)
                    target_node = self._nodes.get(edge.target_key)
                    if target_node:
                        radius.affected_nodes.append(target_node)
                        queue.append((edge.target_key, depth + 1))

        radius.depth = max_depth
        radius.has_ingress_impact = any(
            n.kind in ("Ingress", "HTTPRoute") for n in radius.affected_nodes
        )
        radius.has_data_impact = any(
            n.kind in ("ConfigMap", "Secret", "PersistentVolumeClaim")
            for n in radius.affected_nodes
        )

        # Risk classification heuristic
        if radius.has_ingress_impact or len(radius.affected_nodes) >= 3:
            radius.risk_level = "HIGH"
        elif len(radius.affected_nodes) >= 1:
            radius.risk_level = "MEDIUM"
        else:
            radius.risk_level = "LOW"

        return radius

    def critical_path(self, node_key: str) -> List[GraphNode]:
        """Identify the traffic-facing dependency chain from a node.

        Why: Shows the most critical path through the graph — the chain
             that reaches an Ingress/HTTPRoute (external traffic).

        Algorithm: DFS from node, following edges toward Ingress resources.

        Args:
            node_key: Starting resource key.

        Returns:
            Ordered list of GraphNode objects forming the critical path.
        """
        if node_key not in self._nodes:
            return []

        best_path: List[GraphNode] = []
        ingress_path: List[GraphNode] = []

        def _dfs(
            current: str, visited: Set[str], path: List[GraphNode]
        ) -> None:
            nonlocal best_path, ingress_path

            node = self._nodes.get(current)
            if not node:
                return

            path.append(node)

            if node.kind in ("Ingress", "HTTPRoute") and not ingress_path:
                ingress_path = list(path)

            if len(path) > len(best_path):
                best_path = list(path)

            for edge in self._incoming.get(current, []):
                if edge.source_key not in visited:
                    visited.add(edge.source_key)
                    _dfs(edge.source_key, visited, path)
                    visited.discard(edge.source_key)

            for edge in self._outgoing.get(current, []):
                if edge.target_key not in visited:
                    visited.add(edge.target_key)
                    _dfs(edge.target_key, visited, path)
                    visited.discard(edge.target_key)

            path.pop()

        _dfs(node_key, {node_key}, [])
        return ingress_path if ingress_path else best_path

    def to_dict(self) -> dict:
        """Serialize the full graph for JSON/SARIF export.

        Why: CI/CD pipelines consume structured data. SARIF relatedLocations
             can embed graph context for richer GitHub Security findings.
        """
        return {
            "nodes": [
                {"key": n.key, "kind": n.kind, "namespace": n.namespace, "name": n.name}
                for n in self.get_all_nodes()
            ],
            "edges": [
                {
                    "source": e.source_key,
                    "target": e.target_key,
                    "type": e.edge_type.value,
                    "confidence": e.confidence,
                }
                for e in self._edges
            ],
            "stats": {
                "node_count": self.node_count,
                "edge_count": self.edge_count,
            },
        }

    # =====================================================================
    # INTERNAL (Private)
    # =====================================================================

    def _add_edge(self, edge: GraphEdge) -> None:
        """Register an edge in both directional indexes.

        Why: Bidirectional index enables O(1) lookup for both
             dependents() and dependencies() queries.
        """
        self._edges.append(edge)
        self._outgoing[edge.source_key].append(edge)
        self._incoming[edge.target_key].append(edge)

    def _make_key(self, kind: str, identity: ManifestIdentity) -> str:
        """Build a node key from kind and identity.

        Why: Consistent key construction prevents namespace-related
             lookup misses.
        """
        ns = identity.namespace or "default"
        return f"{kind}/{ns}/{identity.name}"
