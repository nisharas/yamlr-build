#!/usr/bin/env python3
"""
Yamlr REFERENTIAL ALIGNMENT STAGE
----------------------------------
Stage 6.8: Applies cross-resource reference auto-corrections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from yamlr.healers.semantic.reference_healer import ReferenceHealer
from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineStage

__all__ = ['StageReferentialAlignment']


class StageReferentialAlignment(PipelineStage):
    """
    Stage 6.8: Referential Alignment.
    Applies suggestions for missing ConfigMaps/Secrets/PVCs.
    """
    def __init__(self, name: str, healer: "ReferenceHealer"):
        """Initializes the referential alignment stage.
        
        Why: To resolve missing dependencies identified during semantic analysis.
        """
        super().__init__(name)
        self.healer = healer

    def run(self, context: HealContext) -> Dict[str, Any]:
        """Executes referential healing on the current document set.
        
        Why: To repair broken ConfigMap, Secret, and PVC references automatically.
        """
        if not context.docs or not context.findings:
            return {"success": True, "repairs": 0}
            
        fixes = self.healer.heal_docs(context.docs, context.findings)
        
        if fixes > 0:
            context.audit_log.append(f"Stage 6.8: Applied {fixes} referential auto-correction(s)")
            return {"success": True, "repairs": fixes, "penalty": 0} # No penalty for fixing!
            
        return {"success": True, "repairs": 0}
