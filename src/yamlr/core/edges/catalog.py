#!/usr/bin/env python3
"""
Yamlr RESOURCE CATALOG
-----------------------
High-performance indexer for ManifestIdentity objects.
Enables O(1) lookup for edge building, neutralizing O(N^2) bottlenecks.

Why: Moving from nested loops to dictionary-based lookups is the 
     primary defense against "Silent Killer" performance loss 
     on large enterprise codebases.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Set
from yamlr.models import ManifestIdentity

class ResourceCatalog:
    """
    Optimized indexing for K8s resource identities.
    
    Fields indexed:
    - Kind + Name + Namespace (Primary Identity)
    - Kind (Fast filtering)
    - Namespace (Contextual filtering)
    - Container Ports (Workload discovery)
    - Labels (Selector matching)
    """

    def __init__(self, identities: List[ManifestIdentity]):
        self.identities = identities
        
        # O(1) Indexes
        self._by_kind: Dict[str, List[ManifestIdentity]] = defaultdict(list)
        self._by_ns: Dict[str, List[ManifestIdentity]] = defaultdict(list)
        self._by_key: Dict[str, ManifestIdentity] = {} # "Kind/NS/Name"
        
        # Specialized Indexes for Edge Building
        self._by_port: Dict[str, List[ManifestIdentity]] = defaultdict(list)
        self._workload_labels: Dict[str, Dict[str, Dict[str, Set[int]]]] = {} 
        self._id_map: Dict[int, ManifestIdentity] = {}
        # index[ns][label_key][label_val] = {id(identity), ...}

        self._build_indexes()
    def __iter__(self):
        """Allows direct iteration over managed identities."""
        return iter(self.identities)

    def _build_indexes(self):
        """Populate all indexes in a single O(N) pass."""
        for ident in self.identities:
            if not ident.kind:
                continue
            
            ns = ident.namespace or "default"
            name = ident.name or "unnamed"
            
            # Basic Indexes
            self._by_kind[ident.kind].append(ident)
            self._by_ns[ns].append(ident)
            key = f"{ident.kind}/{ns}/{name}"
            self._by_key[key] = ident
            
            # Port Index (for build_port_edges)
            for port in (ident.container_ports or []):
                self._by_port[str(port)].append(ident)
            
            # Label Index (for build_selector_edges)
            # Only index workloads that can be targeted by services
            if ident.kind in ("Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Pod") and ident.labels:
                ns_idx = self._workload_labels.setdefault(ns, {})
                for k, v in ident.labels.items():
                    ns_idx.setdefault(k, {}).setdefault(str(v), set()).add(id(ident))
            
            # Global ID Map for fast reconstruction
            self._id_map[id(ident)] = ident

    def get_by_kind(self, kind: str) -> List[ManifestIdentity]:
        """Returns all resources of a specific kind (O(1))."""
        return self._by_kind.get(kind, [])

    def get_by_key(self, kind: str, namespace: str, name: str) -> Optional[ManifestIdentity]:
        """Returns a specific resource (O(1))."""
        ns = namespace or "default"
        return self._by_key.get(f"{kind}/{ns}/{name}")

    def get_workloads_by_port(self, port: str) -> List[ManifestIdentity]:
        """Returns workloads exposing a specific container port (O(1))."""
        return self._by_port.get(str(port), [])

    def find_matching_workloads(self, namespace: str, selector: Dict[str, str]) -> List[ManifestIdentity]:
        """
        Finds workloads matching a specific label selector in a namespace.
        Optimized via intersection of indexed label sets.
        """
        if not selector:
            return []
            
        ns = namespace or "default"
        ns_idx = self._workload_labels.get(ns)
        if not ns_idx:
            return []
            
        matches: Optional[Set[int]] = None
        
        for k, v in selector.items():
            val_matches = ns_idx.get(k, {}).get(str(v), set())
            if not val_matches:
                return [] # Early exit: one label doesn't match
            
            if matches is None:
                matches = val_matches.copy()
            else:
                matches.intersection_update(val_matches)
                if not matches:
                    return []
        
        if not matches:
            return []
            
        # Map IDs back to objects via pre-built index (O(1) per match)
        return [self._id_map[idx] for idx in matches if idx in self._id_map]
