#!/usr/bin/env python3
"""
Yamlr RESOURCE DEPENDENCY GRAPH
---------------------------------
Builds a typed dependency graph from ManifestIdentity objects.

### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-02-28: Resource Comparison via Catalog**
   - **Context**: Edge building was O(N²) due to nested loops.
   - **Decision**: Introduce `ResourceCatalog` for O(1) membership and selector matching.
   - **Consequence**: Sub-second graph construction for 500+ resources.

2. **2026-03-24: Risk Level Impact Logic**
   - **Context**: "Blast Radius" needed to be more than just a node count.
   - **Decision**: Add `has_ingress_impact` and `has_data_impact` flags.
   - **Consequence**: High-fidelity risk scoring based on proximity to sensitive resources.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Generator, List, Optional, Set, Union

from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.resource_graph")

__all__ = ["BlastRadius", "ResourceGraph"]


from yamlr.core.graph_models import EdgeType, GraphEdge, GraphNode


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
    """Kubernetes resource dependency graph with 17 typed edge categories."""

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

    def build(self, identities: Union[List[ManifestIdentity], Generator[ManifestIdentity, None, None]]) -> None:
        """Construct the graph from a list (or generator) of ManifestIdentity objects.

        Why: Single entry-point for graph construction ensures deterministic
             ordering. Supporting generators prevents OOM during global analysis.
        """
        # [Zero-Blindspot] Materialize generator into a list once for multi-pass use.
        # Identity metadata is lightweight (placeholders), so this is RAM-safe.
        if not isinstance(identities, list):
            identities = list(identities)

        # Lazy imports to avoid circular dependency
        from yamlr.core.edges.catalog import ResourceCatalog

        self._nodes.clear()
        self._edges.clear()
        self._outgoing.clear()
        self._incoming.clear()

        # Phase 1: Index all resources as nodes
        # Also build the high-performance catalog for O(1) edge building
        catalog = ResourceCatalog(identities)
        self._index_nodes(identities)

        # Phase 2: Build all typed edges via registry
        self._build_edges(identities, catalog)

    def _index_nodes(self, identities: List[ManifestIdentity]) -> None:
        """Helper to index all identities as graph nodes."""
        for identity in identities:
            if not identity.kind or not identity.name:
                continue
            namespace = identity.namespace or "default"
            node = GraphNode(
                kind=identity.kind,
                namespace=namespace,
                name=identity.name,
                identity=identity,
                file_path=str(identity.file_path or ""),
            )
            self._nodes[node.key] = node

    def _build_edges(self, identities: List[ManifestIdentity], catalog: Any) -> None:
        """Helper to coordinate edge construction (Native vs. Python fallback)."""
        # [ACCELERATION] Use Native Rust Engine if available and not explicitly disabled
        use_native = False
        native_fn = None

        if os.getenv("YAMLR_DISABLE_NATIVE") == "1":
            logger.debug("Native graph acceleration disabled via YAMLR_DISABLE_NATIVE")
        else:
            try:
                # Try both possible module names for dev/install parity
                from yamlr.native import build_graph_edges as nfn_local

                native_fn = nfn_local
                use_native = True
            except (ImportError, AttributeError, SystemError):
                try:
                    from yamlr_native import build_graph_edges as nfn_pkg

                    native_fn = nfn_pkg
                    use_native = True
                except (ImportError, AttributeError, SystemError):
                    logger.debug("Native acceleration not available, falling back to Python edge builders")

        if use_native and native_fn:
            self._build_native_edges(identities, native_fn)

            # [FIDELITY GUARD] If native returned 0 edges but nodes exist, fallback to Python
            if self.edge_count == 0 and self.node_count > 5:
                logger.warning(
                    "Native graph acceleration returned 0 edges for %d nodes. "
                    "Falling back to Python edge builders for security fidelity.",
                    self.node_count,
                )
                self._build_python_edges(catalog)
        else:
            self._build_python_edges(catalog)

    def _build_native_edges(self, identities: List[ManifestIdentity], build_func: Any) -> None:
        """Helper to invoke native Rust edge builder."""
        # Dynamically resolve NativeIdentity from the same module as build_func
        import sys

        module = sys.modules[build_func.__module__]
        native_identity_class = module.NativeIdentity

        native_idents = []
        for idt in identities:
            if not idt.kind or not idt.name:
                continue
            native_idents.append(
                native_identity_class(
                    kind=idt.kind,
                    name=idt.name,
                    namespace=idt.namespace or "default",
                    labels=idt.labels,
                    selector=idt.selector,
                    config_refs=idt.config_refs,
                    secret_refs=idt.secret_refs,
                    volume_refs=idt.volume_refs,
                    service_refs=idt.service_refs,
                    role_refs=idt.role_refs,
                    cluster_role_refs=idt.cluster_role_refs,
                    service_account=idt.service_account,
                )
            )

        native_edges = build_func(native_idents)
        edge_count = 0
        for ne in native_edges:
            try:
                etype = EdgeType(ne.edge_type)
                self._add_edge(GraphEdge(source_key=ne.source, target_key=ne.target, edge_type=etype, confidence=1.0))
                edge_count += 1
            except (ValueError, KeyError):
                continue
        logger.info(f"Native Graph built: {len(self._nodes)} nodes, {edge_count} edges (Accelerated)")

    def _build_python_edges(self, catalog: Any) -> None:
        """Helper to invoke standard Python edge builders."""
        from yamlr.core.graph_edges import ALL_EDGE_BUILDERS

        for builder in ALL_EDGE_BUILDERS:
            builder(catalog, self._add_edge, self._make_key)

        logger.debug(f"Graph built: {len(self._nodes)} nodes, {len(self._edges)} edges")

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
        """
        radius = BlastRadius(source_key=node_key)
        if node_key not in self._nodes:
            return radius

        _, max_depth = self._perform_impact_search(node_key, radius)
        radius.depth = max_depth
        self._calculate_impact_flags(radius)
        radius.risk_level = self._classify_impact_risk(radius)

        return radius

    def _perform_impact_search(self, start_key: str, radius: BlastRadius) -> Tuple[Set[str], int]:
        """Performs BFS to find all reachable downstream and upstream nodes for impact analysis.

        Why: Decouples search logic from result formatting and risk classification.
        """
        max_depth = 0

        from yamlr.core.graph.algorithms import GraphTraverser

        # Use GraphTraverser to find all reachable nodes (both directions for blast radius)
        # We need to combine incoming and outgoing edges to simulate an undirected search for impact
        # For blast radius, we consider any node connected to the source as "affected"
        all_reachable_keys, max_depth = GraphTraverser.get_all_reachable_nodes_with_depth(
            start_key, self._nodes, self._outgoing, self._incoming
        )

        # Populate radius.affected_nodes and determine max_depth
        # The start_key itself is not "affected" in the context of blast radius, but the source
        # of the blast. So we remove it from the set of affected nodes.
        for key in all_reachable_keys:
            if key != start_key:
                node = self._nodes.get(key)
                if node:
                    radius.affected_nodes.append(node)

        return all_reachable_keys, max_depth

    def _calculate_impact_flags(self, radius: BlastRadius) -> None:
        """Determines if the impact reaches sensitive resource categories.

        Why: Categorizes impact for specialized security reasoning.
        """
        radius.has_ingress_impact = any(n.kind in ("Ingress", "HTTPRoute") for n in radius.affected_nodes)
        radius.has_data_impact = any(
            n.kind in ("ConfigMap", "Secret", "PersistentVolumeClaim") for n in radius.affected_nodes
        )

    def _classify_impact_risk(self, radius: BlastRadius) -> str:
        """Heuristic risk classification based on impact reach and depth.

        Why: Provides a simple "risk tier" for quick developer judgment.
        """
        if radius.has_ingress_impact or len(radius.affected_nodes) >= 3:
            return "HIGH"
        if len(radius.affected_nodes) >= 1:
            return "MEDIUM"
        return "LOW"

    def find_cycles(self) -> List[List[str]]:
        """
        Detects all elementary cycles in the dependency graph.
        Why: Circular dependencies are a critical forensic risk (Deadlock/Flapping).
        """
        from yamlr.core.graph.algorithms import GraphTraverser

        return GraphTraverser.find_cycles(self._nodes, self._outgoing)

    def get_impact_density(self, node_key: str) -> float:
        """
        Calculates the percentage of the cluster (graph nodes) affected by a resource.
        Why: Quantifies impact for forensic risk prioritization.
        """
        if self.node_count == 0:
            return 0.0
        radius = self.blast_radius(node_key)
        # We include the source node in the numerator for "affected" count
        affected_count = len(radius.affected_nodes) + 1
        return (affected_count / self.node_count) * 100.0

    def critical_path(self, node_key: str) -> List[GraphNode]:
        """Identify the traffic-facing dependency chain from a node.

        Why: Shows the most critical path through the graph — the chain
             that reaches an Ingress/HTTPRoute (external traffic).
        """
        if node_key not in self._nodes:
            return []

        paths = self._find_all_paths(node_key)

        # Priority 1: Traffic-facing (Ingress-reaching) path
        for path in paths:
            if any(n.kind in ("Ingress", "HTTPRoute") for n in path):
                return path

        # Priority 2: Longest path (max blast radius)
        if not paths:
            return []
        return max(paths, key=len)

    def _find_all_paths(self, start_key: str) -> List[List[GraphNode]]:
        """Finds all non-cyclic paths from a starting node.

        Why: Decomposes path discovery from selection logic.
        """
        all_paths: List[List[GraphNode]] = []

        def _dfs(current: str, visited: Set[str], current_path: List[GraphNode]):
            node = self._nodes.get(current)
            if not node:
                return

            new_path = current_path + [node]
            all_paths.append(new_path)

            # Explore neighbors (both directions to find relationship chains)
            neighbors = set()
            for e in self._incoming.get(current, []):
                neighbors.add(e.source_key)
            for e in self._outgoing.get(current, []):
                neighbors.add(e.target_key)

            for next_key in neighbors:
                if next_key not in visited:
                    _dfs(next_key, visited | {next_key}, new_path)

        _dfs(start_key, {start_key}, [])
        return all_paths

    def to_dict(self) -> dict:
        """Serialize the full graph for JSON/SARIF export.

        Why: CI/CD pipelines consume structured data. SARIF relatedLocations
             can embed graph context for richer GitHub Security findings.
        """
        return {
            "nodes": [
                {"key": n.key, "kind": n.kind, "namespace": n.namespace, "name": n.name} for n in self.get_all_nodes()
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

    def prune_nodes_for_file(self, file_path: Path) -> None:
        """
        Removes all nodes associated with a specific file path.
        Why: Prevents 'Phantom Nodes' and memory leaks in long-running processes
             or multi-file hyperscale sessions.
        """
        target_str = str(file_path).replace("\\", "/")
        keys_to_remove = [k for k, node in self._nodes.items() if node.file_path.replace("\\", "/") == target_str]

        for key in keys_to_remove:
            # Clean up the edge indices
            # Note: We keep the edge in _edges for history, but O(1) lookups are removed
            self._outgoing.pop(key, None)
            self._incoming.pop(key, None)
            # Remove from edges list to maintain consistency
            self._edges = [e for e in self._edges if e.source_key != key and e.target_key != key]
            # Remove node
            del self._nodes[key]

        if keys_to_remove:
            logger.debug(f"Pruned {len(keys_to_remove)} nodes for {target_str}")

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
