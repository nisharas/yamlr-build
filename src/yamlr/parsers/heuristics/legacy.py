from __future__ import annotations
from typing import Any, Dict
from .base import BaseHeuristic

__all__ = ['LegacyMarkerHeuristic']

class LegacyMarkerHeuristic(BaseHeuristic):
    """
    Identifies legacy YAML markers that are often present in K8s manifests but 
    not part of the standard OpenAPI schema, preventing scanner noise.
    
    Why: LEGACY AUDIT V23. Markers like merge keys (<<), directives (%), 
    and complex keys (?) are valid YAML but "Ghost Logic" in K8s. 
    Yamlr tags them for awareness rather than reporting them as errors.
    """

    @property
    def name(self) -> str:
        return "legacy_marker_tagger"

    @property
    def description(self) -> str:
        return "Tags legacy YAML markers (<<, %, ?) to avoid schema noise"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """
        Tags legacy markers to avoid scanner noise.
        """
        stripped = line.lstrip()
        tags = context.get("pending_tags", [])
        
        # 1. Merge Key (<<: *ref)
        if stripped.startswith("<<:") or stripped.startswith("<< :"):
             tags.append("yamlr.intent:legacy-marker")
             
        # 2. Document Directive (%YAML 1.2)
        elif stripped.startswith("%"):
             tags.append("yamlr.intent:legacy-marker")
             
        # 3. Complex Key (? key: value)
        elif stripped.startswith("? "):
             tags.append("yamlr.intent:legacy-marker")

        return line
