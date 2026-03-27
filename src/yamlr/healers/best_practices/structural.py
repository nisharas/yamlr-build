#!/usr/bin/env python3
"""
Yamlr STRUCTURAL HEALER
-----------------------
Handles cross-cutting structural repairs and normalization.
Decomposed and Hardened: v1.1 Refactor.

Author: Antigravity / Yamlr Team
Date: 2026-03-20
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from yamlr.core.context import HealContext

logger = logging.getLogger("yamlr.healers.structural")
__all__ = ['StructuralHealer']

class StructuralHealer:
    """
    Stabilizes Kubernetes manifests by normalizing structural issues.
    """

    def heal_doc(self, doc: Dict[str, Any], context: Optional[HealContext] = None) -> bool:
        """
        Executes structural normalization on a single document.
        """
        modified = False
        
        # 1. Normalize EnvFrom blocks
        if self.normalize_envfrom(doc, context):
            modified = True
            
        return modified

    def normalize_envfrom(self, doc: Dict[str, Any], context: Optional[HealContext] = None) -> bool:
        """
        Fix envFrom blocks and lift misnested fields.
        
        Why: Kubernetes users sometimes place container properties 
             (like ports or resources) inside the envFrom list item.
        """
        if doc is None:
            return False

        kind = str(doc.get("kind") or "").lower()
        spec = doc.get("spec")
        if not spec or not hasattr(spec, "__getitem__"):
            return False

        # Pod spec resolution
        pod_spec = spec if kind == "pod" else spec.get("template", {}).get("spec")
        if not pod_spec or not hasattr(pod_spec, "__getitem__"):
            return False
        
        containers = pod_spec.get("containers") or []
        modified = False

        for container in [c for c in containers if isinstance(c, dict)]:
            env_from = container.get("envFrom")
            if not env_from:
                continue

            # Standardize to list
            if isinstance(env_from, dict):
                env_from = [env_from]
                container["envFrom"] = env_from
                modified = True

            if not isinstance(env_from, list):
                continue

            for item in [i for i in env_from if isinstance(i, dict)]:
                if self._lift_misnested_fields(container, item, context):
                    modified = True
                if self._repair_ref_structure(item, context):
                    modified = True

        return modified

    def _lift_misnested_fields(self, container: dict, item: dict, context: Optional[HealContext]) -> bool:
        """Helper to safely lift misnested fields out of envFrom items."""
        modified = False
        # [Security] Lifting Guard (T1505.003)
        for key in ("ports", "readinessProbe", "livenessProbe", "resources"):
            if key in item and key not in container:
                val = item.get(key)
                is_valid = (key == "ports" and isinstance(val, (list, tuple))) or \
                           (key in ("readinessProbe", "livenessProbe", "resources") and isinstance(val, dict))
                
                if is_valid:
                    container[key] = item.pop(key)
                    modified = True
                    if context:
                        from yamlr.core.stages.boundaries import MutationScope
                        from yamlr.models import HealAction
                        context.prescribe(HealAction(
                            stage="Shield",
                            action_type="repair",
                            target=f"containers[{container.get('name', 'unknown')}].{key}",
                            description=f"Structural Cleanup: Lifted validated field '{key}' out of envFrom",
                            rationale=f"Kubernetes requires '{key}' to be a direct property of the container, while it was found misnested inside an envFrom block.",
                            suggestion=f"Move '{key}' to the container level (sibling of envFrom).",
                            severity="info",
                            rule_id="rule/misnested-envfrom",
                            scope=MutationScope.STRUCTURAL
                        ))
                else:
                    logger.warning(f"Security: Blocked lifting of invalid '{key}' type from envFrom.")
        return modified

    def _repair_ref_structure(self, item: dict, context: Optional[HealContext]) -> bool:
        """Helper to repair configMapRef/secretRef structures."""
        modified = False
        for ref_key in ("configMapRef", "secretRef"):
            if ref_key in item:
                ref = item.get(ref_key)
                if ref is None or not isinstance(ref, dict):
                    ref = {}
                    item[ref_key] = ref
                if "name" in item and "name" not in ref:
                    ref["name"] = item.pop("name")
                    modified = True
                    if context:
                        from yamlr.core.stages.boundaries import MutationScope
                        from yamlr.models import HealAction
                        context.prescribe(HealAction(
                            stage="Shield",
                            action_type="repair",
                            target=f"envFrom.{ref_key}",
                            description=f"Structural Cleanup: Repaired {ref_key} structure",
                            rationale=f"The {ref_key} block was missing its required 'name' field, which was found at the wrong nesting level.",
                            suggestion=f"Ensure '{ref_key}' contains the resource name target correctly.",
                            severity="info",
                            rule_id="rule/malformed-ref",
                            scope=MutationScope.STRUCTURAL
                        ))
        return modified
