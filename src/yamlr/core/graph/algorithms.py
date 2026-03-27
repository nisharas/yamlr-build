#!/usr/bin/env python3
"""
Yamlr GRAPH ALGORITHMS
-----------------------
Pure traversal logic for ResourceGraph nodes.
Decoupled from Graph models to ensure M&A-ready modularity.

Why: Moving traversal logic out of the main ResourceGraph class 
     satisfies the "Ingestability Test" and makes algorithms reusable.
"""

from yamlr.core.graph_models import GraphNode, GraphEdge

MAX_RECURSION_DEPTH = 32 # Anti-Deadlock Guard for Enterprise manifests

class GraphTraverser:
    """Helper for standard graph traversal patterns."""
    
    @staticmethod
    def get_descendants(
        start_node_key: str, 
        nodes: Dict[str, GraphNode], 
        outgoing: Dict[str, List[GraphEdge]]
    ) -> Set[str]:
        """Returns all reachable node keys via BFS."""
        visited = set()
        queue = [start_node_key]
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            edges = outgoing.get(current, [])
            for edge in edges:
                if edge.target_key not in visited:
                    queue.append(edge.target_key)
        
        return visited

    @staticmethod
    def get_all_reachable_nodes_with_depth(
        start_key: str,
        nodes: Dict[str, GraphNode],
        outgoing: Dict[str, List[GraphEdge]],
        incoming: Dict[str, List[GraphEdge]]
    ) -> Tuple[Set[str], int]:
        """BFS that explores in both directions to find the full 'blast radius'."""
        visited = {start_key}
        queue = [(start_key, 0)]
        max_depth = 0
        
        while queue:
            current_key, depth = queue.pop(0)
            if depth >= MAX_RECURSION_DEPTH:
                continue
            max_depth = max(max_depth, depth)
            
            # Combine incoming/outgoing for bidirectional "impact"
            adj_edges = outgoing.get(current_key, []) + incoming.get(current_key, [])
            for edge in adj_edges:
                # Target depends on direction
                neighbor = edge.target_key if edge.source_key == current_key else edge.source_key
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        
        return visited, max_depth

    @staticmethod
    def find_cycles(
        nodes: Dict[str, GraphNode], 
        outgoing: Dict[str, List[GraphEdge]]
    ) -> List[List[str]]:
        """
        Detects all elementary cycles in the dependency graph using Tarjan's/DFS.
        Why: Circular dependencies can cause "Deadlock Manifests" where neither 
             resource can be healthy until the other is finalized.
        Returns:
            List of cycles, where each cycle is a list of node keys.
        """
        cycles = []
        visited = set()
        on_stack = set()
        path = []

        def _dfs(u: str):
            visited.add(u)
            on_stack.add(u)
            path.append(u)

            for edge in outgoing.get(u, []):
                v = edge.target_key
                if v not in visited:
                    _dfs(v)
                elif v in on_stack:
                    # Cycle detected: extract from path
                    idx = path.index(v)
                    cycles.append(path[idx:] + [v])

            on_stack.remove(u)
            path.pop()

        for node_key in sorted(nodes.keys()):
            if node_key not in visited:
                _dfs(node_key)

        return cycles

    @staticmethod
    def get_topological_sort(
        nodes: Dict[str, GraphNode], 
        outgoing: Dict[str, List[GraphEdge]],
        incoming: Dict[str, List[GraphEdge]]
    ) -> List[str]:
        """Returns node keys in dependency order (Kahn's Algorithm)."""
        # 1. Calculate in-degrees
        in_degree = GraphTraverser._calculate_in_degrees(nodes, outgoing)
        
        # 2. Queue nodes with 0 in-degree
        queue = [k for k, v in in_degree.items() if v == 0]
        sorted_keys = []
        
        while queue:
            # Sort queue for determinism
            queue.sort()
            u_key = queue.pop(0)
            sorted_keys.append(u_key)
            
            for edge in outgoing.get(u_key, []):
                v_key = edge.target_key
                if v_key in in_degree:
                    in_degree[v_key] -= 1
                    if in_degree[v_key] == 0:
                        queue.append(v_key)
        
        GraphTraverser._check_for_partial_sort(len(sorted_keys), len(nodes))
        return sorted_keys

    @staticmethod
    def _calculate_in_degrees(nodes: Dict[str, GraphNode], outgoing: Dict[str, List[GraphEdge]]) -> Dict[str, int]:
        """Helper to calculate in-degree for all nodes."""
        in_degree = dict.fromkeys(nodes, 0)
        for edges in outgoing.values():
            for edge in edges:
                if edge.target_key in in_degree:
                    in_degree[edge.target_key] += 1
        return in_degree

    @staticmethod
    def _check_for_partial_sort(sorted_count: int, total_count: int) -> None:
        """Logs a warning if a topological sort was incomplete due to cycles."""
        if sorted_count != total_count:
            import logging
            lg = logging.getLogger("yamlr.resource_graph")
            lg.warning(
                f"Topological sort incomplete: {total_count - sorted_count} "
                f"nodes involved in cycles. Returning partial sort."
            )
