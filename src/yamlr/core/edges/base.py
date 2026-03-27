#!/usr/bin/env python3
"""
Yamlr GRAPH EDGE BASE
---------------------
Shared types and utilities for edge construction.
"""

from __future__ import annotations
from typing import Callable, Dict, Optional
from yamlr.models import ManifestIdentity
from yamlr.core.graph_models import GraphEdge

# Type aliases for edge construction
AddEdgeFn = Callable[[GraphEdge], None]
MakeKeyFn = Callable[[str, ManifestIdentity], str]
__all__ = ['labels_match']


def labels_match(selector: Optional[Dict[str, str]], labels: Optional[Dict[str, str]]) -> bool:
    """
    Check if a selector matches a set of labels.

    Why: Replicates Kubernetes selector semantics — all selector
         keys must exist in labels with matching values.
    """
    if not selector:
        return False
    if not labels:
        return False
    
    for key, value in selector.items():
        if key not in labels or labels[key] != value:
            return False
            
    return True
