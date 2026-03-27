from __future__ import annotations
import sys
from typing import Set, List, Dict, Optional
from rich.console import Console
from rich.tree import Tree
from yamlr.core.resource_graph import ResourceGraph
from yamlr.core.graph_models import GraphNode

__all__ = ['GraphRenderer']

class GraphRenderer:
    """Renders ResourceGraph into human-readable topological views or export formats.
    
    Why: To provide visual observability into resource relationships (topo/mermaid)
         while maintaining a zero-latency, manifest-only engine identity.
    """

    CONSERVATIVE_KINDS = {
        "Namespace", "Deployment", "StatefulSet", "DaemonSet", 
        "Job", "CronJob", "Service", "Ingress", "Gateway", "HTTPRoute"
    }

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console(force_terminal=sys.stdout.isatty())

    def render_topo(self, graph: ResourceGraph, kinds: Optional[Set[str]] = None):
        """Renders an ASCII tree of the resource topology.
        
        Why: Provides a 'Kubevious-style' relational view in the terminal.
        """
        filter_kinds = kinds or self.CONSERVATIVE_KINDS
        nodes = graph.get_all_nodes()
        
        # Group by Namespace
        ns_map: Dict[str, List[GraphNode]] = {}
        for node in nodes:
            if node.kind not in filter_kinds:
                continue
            ns = node.namespace
            if ns not in ns_map:
                ns_map[ns] = []
            ns_map[ns].append(node)

        root = Tree("[bold cyan]Yamlr Topology[/bold cyan]")
        
        for ns, ns_nodes in sorted(ns_map.items()):
            ns_tree = root.add(f"[bold yellow]Namespace: {ns}[/bold yellow]")
            
            # Start from 'Entry' points (Ingress/Gateway)
            entries = [n for n in ns_nodes if n.kind in ("Ingress", "Gateway", "HTTPRoute")]
            visited: Set[str] = set()
            
            for entry in sorted(entries, key=lambda x: x.name):
                self._build_tree_recursive(ns_tree, entry, graph, visited, filter_kinds)
            
            # Add orphaned workloads (not reached from Ingress)
            orphans = [n for n in ns_nodes if n.kind in ("Deployment", "StatefulSet", "DaemonSet") and n.key not in visited]
            if orphans:
                orphan_branch = ns_tree.add("[dim]Other Workloads[/dim]")
                for orphan in sorted(orphans, key=lambda x: x.name):
                    self._build_tree_recursive(orphan_branch, orphan, graph, visited, filter_kinds)

        self.console.print(root)

    def _build_tree_recursive(self, parent_tree: Tree, node: GraphNode, graph: ResourceGraph, visited: Set[str], filter_kinds: Set[str]):
        """Recursively builds the rich tree branch."""
        if node.key in visited:
            parent_tree.add(f"[dim](link) {node.kind}/{node.name}[/dim]")
            return
        
        visited.add(node.key)
        
        icon = self._get_kind_icon(node.kind)
        branch = parent_tree.add(f"{icon} [bold]{node.kind}[/bold]/{node.name}")
        
        # Traverse downstream (dependents) for traffic flow
        # In Yamlr, Service depends on Deployment, Ingress depends on Service.
        # So for Traffic Flow (Ingress -> Service -> Deployment), we follow dependencies()
        deps = graph.dependencies(node.key)
        for dep in sorted(deps, key=lambda x: (x.kind, x.name)):
            if dep.kind in filter_kinds:
                self._build_tree_recursive(branch, dep, graph, visited, filter_kinds)

    def render_mermaid(self, graph: ResourceGraph, kinds: Optional[Set[str]] = None) -> str:
        """Generates a Mermaid.js graph specification.
        
        Why: Enables integration with IDPs (Backstage) and docs (Notion/GitHub).
        """
        filter_kinds = kinds or self.CONSERVATIVE_KINDS
        lines = ["graph TD"]
        
        # 1. Define Nodes
        nodes = graph.get_all_nodes()
        node_ids: Dict[str, str] = {}
        for i, node in enumerate(nodes):
            if node.kind not in filter_kinds:
                continue
            # sanitize id
            node_id = f"node_{i}"
            node_ids[node.key] = node_id
            label = f"{node.kind}/{node.name}"
            lines.append(f"  {node_id}[\"{label}\"]")

        # 2. Define Edges
        # We need to access private edges for full fidelity or use dict
        graph_dict = graph.to_dict()
        for edge in graph_dict.get("edges", []):
            src = edge["source"]
            tgt = edge["target"]
            if src in node_ids and tgt in node_ids:
                lines.append(f"  {node_ids[src]} --> {node_ids[tgt]}")

        return "\n".join(lines)

    def _get_kind_icon(self, kind: str) -> str:
        """Returns a terminal-friendly icon for the resource kind."""
        icons = {
            "Namespace": "📁",
            "Deployment": "🚀",
            "StatefulSet": "💾",
            "DaemonSet": "😈",
            "Service": "🔌",
            "Ingress": "🌐",
            "Gateway": "🏢",
            "HTTPRoute": "🛣️",
            "ConfigMap": "⚙️",
            "Secret": "🔑"
        }
        return icons.get(kind, "📄")
