#!/usr/bin/env python3
"""
Yamlr DETECTORS BASE
--------------------
Shared utilities and base classes for cross-resource detection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Set

if TYPE_CHECKING:
    from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzer.detectors.base")

def build_index(identities: List[ManifestIdentity]) -> Dict[str, Dict[str, Set[str]]]:
    """Builds a lookup index for O(1) existence checks.
    
    Why: Shared between sequential and parallel resolution paths.
    """
    index: Dict[str, Dict[str, Set[str]]] = {
        k: {} for k in [
            "ConfigMap", "Secret", "PersistentVolumeClaim", "Service",
            "ServiceAccount", "Role", "ClusterRole", "StorageClass",
            "IngressClass", "PriorityClass", "RuntimeClass"
        ]
    }
    
    for ident in identities:
        if not ident.kind or not ident.name: continue
        k, ns = ident.kind, ident.namespace or "default"
        if k in index:
            index[k].setdefault(ns, set()).add(ident.name)
    return index
