#!/usr/bin/env python3
"""
Yamlr TRAFFIC DETECTORS
-----------------------
Detection algorithms for K8s Traffic resources (Service, Ingress).
"""

from __future__ import annotations

import difflib
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from yamlr.core.resource_graph import ResourceGraph
    from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzer.detectors.traffic")


def detect_ghost_services(
    services: List[ManifestIdentity],
    workloads: List[ManifestIdentity],
    pro_mode: bool = False,
    graph: Optional["ResourceGraph"] = None,
) -> List[Dict]:
    """Detects Services with selectors that match no Pods."""
    ghost_services = []

    # O(N) Optimization: If graph is available, use it to check for SELECTOR_MATCH edges
    if graph:
        from yamlr.core.graph_models import EdgeType

        for service in services:
            if not service.selector:
                continue
            svc_key = f"Service/{service.namespace or 'default'}/{service.name}"

            # Check for SELECTOR_MATCH outgoing edges
            outgoing = graph._outgoing.get(svc_key, [])
            has_pod_match = any(e.edge_type == EdgeType.SELECTOR_MATCH for e in outgoing)

            if not has_pod_match:
                hint = _generate_hint(service, workloads, pro_mode)
                ghost_services.append(
                    {
                        "name": service.name,
                        "namespace": service.namespace or "default",
                        "hint": hint,
                        "file_path": getattr(service, "file_path", "unknown"),
                    }
                )
        return ghost_services

    # Fallback to legacy indexing logic
    workload_index: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    for w in workloads:
        ns = w.namespace or "default"
        if not w.labels:
            continue

        ns_idx = workload_index.setdefault(ns, {})
        for k, v in w.labels.items():
            ns_idx.setdefault(str(k), {}).setdefault(str(v), []).append(w.name)

    for service in services:
        if not service.selector:
            continue

        ns = service.namespace or "default"
        ns_idx = workload_index.get(ns, {})

        if not ns_idx:
            matches = []
        else:
            match_sets = []
            for k, v in service.selector.items():
                val_matches = ns_idx.get(str(k), {}).get(str(v), [])
                if not val_matches:
                    match_sets = []
                    break
                match_sets.append(set(val_matches))

            if not match_sets:
                matches = []
            else:
                matches = list(set.intersection(*match_sets))

        if not matches:
            hint = _generate_hint(service, workloads, pro_mode)
            ghost_services.append(
                {
                    "name": service.name,
                    "namespace": ns,
                    "hint": hint,
                    "file_path": getattr(service, "file_path", "unknown"),
                }
            )
    return ghost_services


def labels_match(selector: Dict[str, str], labels: Dict[str, str]) -> bool:
    """Checks if a selector matches a set of labels (Robust)."""
    for key, value in selector.items():
        target = labels.get(key)
        if target is None or str(target).strip() != str(value).strip():
            return False
    return True


def _generate_hint(service: ManifestIdentity, workloads: List[ManifestIdentity], pro_mode: bool) -> str:
    """Generates an actionable hint for fixing a ghost service."""
    selector_yaml = "\n        ".join(f"{k}: {v}" for k, v in service.selector.items())
    hint = f"Add a Deployment with matching labels:\n    spec:\n      template:\n        metadata:\n          labels:\n            {selector_yaml}"

    if len(workloads) > 1000:
        return hint + "\n    (Fuzzy matching disabled for large datasets to maintain performance)"

    candidates = []
    for w in workloads:
        if not w.labels:
            continue
        if any(k in (w.labels or {}) for k in (service.selector or {})):
            score = sum(
                difflib.SequenceMatcher(None, f"{k}={v}", f"{wk}={wv}").ratio()
                for k, v in (service.selector or {}).items()
                for wk, wv in (w.labels or {}).items()
                if k == wk or difflib.SequenceMatcher(None, k, wk).ratio() > 0.8
            )
            if score > 0.7 * len(service.selector or {}):
                candidates.append(f"{w.kind}/{w.name}")

    if candidates:
        hint += f"\n\n    💡 Potential matches found: {', '.join(candidates[:3])}"

    if pro_mode:
        hint += "\n    (Enterprise mode will auto-generate this in a future release)"
    return hint
