"""
Yamlr REFERENCE RESOLVER
------------------------
Implements the core two-pass reference validation logic.
Identifies missing ConfigMaps, Secrets, Services, PVCs, and RBAC resources.

Why: Enables cross-resource validation by indexing all known manifests 
     and checking references against the constructed index.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from yamlr.core.resource_graph import ResourceGraph

from yamlr.analyzers.base import AnalysisResult
from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzers.ref_resolver")
__all__ = ['ReferenceResolver']

class ReferenceResolver:
    """
    Performs Cross-Resource Validation (Pass 1: Indexing, Pass 2: Checking).
    Identifies missing ConfigMaps, Secrets, Services, PVCs.
    """
    
    def __init__(self, graph: Optional["ResourceGraph"] = None):
        """
        Why: Unifies reference resolution with the safety engine's resource graph.
        """
        self.graph = graph

    def resolve_references(self, identities: List[ManifestIdentity], index: Optional[Dict] = None) -> List[AnalysisResult]:
        """
        Scans all identifies to find broken references.
        Returns a list of AnalysisResult objects.
        """
        from yamlr.analyzers.detectors import CrossResourceDetectors
        
        # Call the unified detector (O(N) fallback, O(1) graph, or pre-built index)
        raw_broken = CrossResourceDetectors.detect_broken_refs(identities, graph=self.graph, index=index)
        
        # Convert raw dicts to AnalysisResult objects
        results = []
        # Rule ID Mapping for compatibility with the Rule DB (rules.yaml)
        RULE_MAP = {
            "ConfigMap": "missing-configmap-ref",
            "Secret": "missing-secret-ref",
            "Service": "missing-service-ref",
            "PersistentVolumeClaim": "missing-pvc-ref",
            "ServiceAccount": "missing-serviceaccount-ref",
            "Role": "missing-role-ref",
            "ClusterRole": "missing-clusterrole-ref",
            "IngressClass": "missing-ingressclass-ref",
            "StorageClass": "missing-storageclass-ref",
        }

        for b in raw_broken:
            kind = b['kind']
            rule_id = RULE_MAP.get(kind, "missing-reference")
            
            is_global = b.get('is_global', False)
            location_msg = "in cluster" if is_global else f"in namespace '{b['namespace']}'"
            
            results.append(AnalysisResult(
                analyzer_name="ReferenceResolver",
                # ...
                severity="ERROR",
                message=f"Broken reference: {kind} '{b['name']}' not found {location_msg}.",
                resource_name=b['resource_name'],
                resource_kind=b['resource_kind'],
                file_path=b['file_path'],
                rule_id=rule_id,
                suggestion=b.get('suggestion', f"Ensure {kind} '{b['name']}' exists."),
                fix_available=True,
                fix_id=f"{kind}:{b['name']}:{b['namespace']}"
            ))
        return results
