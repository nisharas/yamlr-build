#!/usr/bin/env python3
"""
Yamlr CONFIG DETECTORS
----------------------
Detection algorithms for K8s Config and RBAC resources (Secret, ConfigMap, RBAC).
"""

from __future__ import annotations

import difflib
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from yamlr.core.resource_graph import ResourceGraph
    from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzer.detectors.config")

def detect_orphan_configs(configs: List[ManifestIdentity], workloads: List[ManifestIdentity]) -> List[Dict]:
    """Detects ConfigMaps/Secrets that no Pod references."""
    referenced_configs = set()
    referenced_secrets = set()
    for w in workloads:
        referenced_configs.update(w.config_refs or [])
        referenced_secrets.update(w.secret_refs or [])

    orphans = []
    for config in configs:
        target_set = referenced_secrets if config.kind == "Secret" else referenced_configs
        if config.name not in target_set:
            orphans.append({
                "kind": config.kind,
                "name": config.name,
                "namespace": config.namespace or "default",
                "file_path": getattr(config, "file_path", "unknown"),
            })
    return orphans

def detect_broken_refs(identities: List[ManifestIdentity], graph: Optional["ResourceGraph"] = None, index: Optional[Dict] = None) -> List[Dict]:
    """Detects broken references (ConfigMaps, Secrets, PVCs, Services, RBAC, etc.)."""
    if graph:
        return _detect_broken_refs_via_graph(identities, graph)

    if index is None:
        from yamlr.analyzers.detectors.base import build_index
        index = build_index(identities)

    return _detect_broken_refs_via_index(identities, index)

def _detect_broken_refs_via_graph(identities: List[ManifestIdentity], graph: "ResourceGraph") -> List[Dict]:
    """Helper for graph-based reference detection."""
    broken = []
    from yamlr.core.graph_models import EdgeType
    for w in identities:
        broken.extend(_check_graph_resource_references(w, graph, EdgeType))
    return broken

def _check_graph_resource_references(w: ManifestIdentity, graph: "ResourceGraph", edge_type_enum: Any) -> List[Dict]:
    """Checks all graph-based references for a single manifest identity."""
    wl_key = f"{w.kind}/{w.namespace or 'default'}/{w.name}"
    outgoing = graph._outgoing.get(wl_key, [])
    broken = []
    
    ref_checks = [
        (w.config_refs, edge_type_enum.CONFIG_REF, "ConfigMap"),
        (w.secret_refs, edge_type_enum.SECRET_REF, "Secret"),
        (w.volume_refs, edge_type_enum.PVC_REF, "PersistentVolumeClaim"),
        (w.service_refs, edge_type_enum.SERVICE_REF, "Service"),
        (w.role_refs, edge_type_enum.ROLE_REF, "Role"),
        (w.cluster_role_refs, edge_type_enum.CLUSTER_ROLE_REF, "ClusterRole"),
        (w.service_account, [edge_type_enum.SERVICE_ACCOUNT_REF] if hasattr(edge_type_enum, 'SERVICE_ACCOUNT_REF') else [], "ServiceAccount"),
    ]
    
    for ref_data, edge_type, kind in ref_checks:
        broken.extend(_check_graph_reference_group(ref_data, edge_type, kind, w, outgoing))
    return broken

def _check_graph_reference_group(ref_data: Any, edge_type: Any, kind: str, w: ManifestIdentity, outgoing: List[Any]) -> List[Dict]:
    """Helper to check a group of graph-based references."""
    if not ref_data: return []
    refs = [ref_data] if isinstance(ref_data, str) else ref_data
    edge_types = edge_type if isinstance(edge_type, list) else [edge_type]
    active_refs = {e.target_key.split("/")[-1] for e in outgoing if e.edge_type in edge_types}
    
    broken = []
    for ref in refs:
        if ref not in active_refs:
            broken.append({
                "kind": kind, "name": ref, "resource_name": w.name,
                "resource_kind": w.kind, "namespace": w.namespace or "default",
                "file_path": getattr(w, "file_path", "unknown"),
                "suggestion": f"Ensure {kind} '{ref}' exists."
            })
    return broken

def _detect_broken_refs_via_index(identities: List[ManifestIdentity], index: Dict) -> List[Dict]:
    """Helper for index-based reference detection."""
    from yamlr.models import CLUSTER_SCOPED_KINDS
    broken = []
    cluster_scoped = CLUSTER_SCOPED_KINDS

    for w in identities:
        broken.extend(_check_resource_references(w, index, cluster_scoped, len(identities)))
    return broken

def _check_resource_references(w: ManifestIdentity, index: Dict, cluster_scoped: List[str], total_count: int) -> List[Dict]:
    """Checks all references for a single manifest identity."""
    broken = []
    checks = [
        (w.config_refs, "ConfigMap"), (w.secret_refs, "Secret"),
        (w.volume_refs, "PersistentVolumeClaim"), (w.service_refs, "Service"),
        (w.role_refs, "Role"), (w.cluster_role_refs, "ClusterRole"),
        (w.storage_class_refs, "StorageClass"), (w.ingress_class_refs, "IngressClass"),
        (w.service_account, "ServiceAccount"),
    ]

    for ref_data, kind in checks:
        broken.extend(_check_reference_group(ref_data, kind, w, index, cluster_scoped, total_count))
    return broken

def _check_reference_group(ref_data: Any, kind: str, w: ManifestIdentity, index: Dict, cluster_scoped: List[str], total_count: int) -> List[Dict]:
    """Helper to check a group of references (e.g., all ConfigMaps)."""
    if not ref_data: return []
    ns = w.namespace or "default"
    broken = []
    refs = [ref_data] if isinstance(ref_data, str) else ref_data
    for ref in refs:
        is_global = kind in cluster_scoped
        lookup_ns = "default" if is_global else ns
        
        # [MEMORY-OPTIMIZED] Support for DiskIndex (SQLite) or legacy Dict index
        if hasattr(index, 'exists'):
            exists = index.exists(kind, lookup_ns, ref)
        else:
            exists = ref in index.get(kind, {}).get(lookup_ns, set())

        if not exists:
            # Skip fuzzy match for ultra-scale to save CPU/Memory
            match = _find_fuzzy_match(ref, kind, index) if (total_count < 500 and not hasattr(index, 'exists')) else None
            broken.append(_build_broken_ref_report(ref, kind, w, ns, is_global, match))
    return broken

def _find_fuzzy_match(ref: str, kind: str, index: Dict) -> Optional[str]:
    """Finds a fuzzy match for a broken reference within the index."""
    all_names = []
    for names in index.get(kind, {}).values():
        all_names.extend(list(names))
    if not all_names: return None
    matches = difflib.get_close_matches(ref, all_names, n=1, cutoff=0.7)
    return matches[0] if matches else None

def _build_broken_ref_report(ref: str, kind: str, w: ManifestIdentity, ns: str, is_global: bool, match: Optional[str]) -> Dict:
    """Constructs a standardized report for a broken reference."""
    location_msg = "in cluster" if is_global else f"in namespace '{ns}'"
    return {
        "kind": kind, "name": ref, "resource_name": w.name,
        "resource_kind": w.kind, "namespace": ns,
        "is_global": is_global,
        "file_path": getattr(w, "file_path", "unknown"),
        "suggestion": f"Use {kind} '{match}'" if match else f"Ensure {kind} '{ref}' exists {location_msg}."
    }
