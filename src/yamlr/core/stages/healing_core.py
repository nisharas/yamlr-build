"""
Yamlr Healing Stage - Core Structural
------------------------------------
What: Repairs selector mismatches, structural orphan keys, and port misalignments.
Why: Structural and connection issues cause 80% of K8s downtime (VAL-02-1).
Where: Executed as part of the Healing Pipeline.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from yamlr.core.stages.base import PipelineStage, StageResult
from yamlr.healers.best_practices.structural import StructuralHealer
from yamlr.healers.best_practices.metadata import MetadataHealer
from yamlr.healers.semantic.selector_healer import ServiceSelectorHealer
from yamlr.healers.semantic.port_healer import PortMismatchHealer
from yamlr.core.stages.boundaries import BoundaryEnforcer, HealerPermit, MutationScope

class HealingCoreStage(PipelineStage):
    """
    Healing Core (Structural & Connection).
    
    Why: To ensure that Services and Deployments are structurally sound and
         aligned according to their label/selector contract.
    """

    def __init__(self, name: str = "HealingCore"):
        super().__init__(name)
        self.structural_healer = StructuralHealer()
        self.metadata_healer = MetadataHealer()
        self.selector_healer = ServiceSelectorHealer()
        self.port_healer = PortMismatchHealer()
        self.permit = HealerPermit(
            "HealingCore", 
            {MutationScope.STRUCTURAL, MutationScope.METADATA, MutationScope.SPEC_SELECTOR, MutationScope.SPEC_PORTS}
        )

    def execute(self, state: PipelineState) -> StageResult:
        """
        Executes core structural healing.
        """
        modified_count = 0
        try:
            # 1. Structural/Metadata Repair (Recursive)
            for doc in state.documents:
                modified_count += self._heal_single_doc(doc, state.context)

            # 2. Semantic Cross-Resource Repair
            modified_count += self._heal_multi_doc_relationships(state)

            return StageResult(
                success=True,
                metadata={"modified": modified_count}
            )
        except Exception as e:
            logger.error(f"HealingCoreStage failed: {e}")
            return StageResult(success=False, errors=[str(e)])

    def _heal_single_doc(self, data: Any, context: Any) -> int:
        """Helper to process a single document's structural healing with Phase 14 Isolation."""
        modified = 0
        
        def _safe_call(healer_func, *args, **kwargs):
             try:
                 return healer_func(*args, **kwargs)
             except Exception as e:
                 msg = f"⚠️ Non-Fatal Rule Fault in {healer_func.__qualname__}: {e}"
                 logger.warning(msg)
                 if hasattr(context, "audit_log"):
                     context.audit_log.append(msg)
                 return False

        # 1. Metadata / Orphan Keys
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.METADATA, context):
            if _safe_call(self.metadata_healer.fix_orphans, data, context):
                modified += 1

        # 2. Structural Cleanup (EnvFrom, etc)
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.STRUCTURAL, context):
            if _safe_call(self.structural_healer.heal_doc, data, context):
                modified += 1

        # 3. Selector/Port Alignment (Semantic)
        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_SELECTOR, context):
            if _safe_call(self.selector_healer.normalize_deployment_selector, data, context):
                modified += 1
        return modified

    def _heal_multi_doc_relationships(self, state: PipelineState) -> int:
        """Helper to process cross-resource semantic alignment with Isolation."""
        modified = 0
        context = state.context

        def _safe_call(healer_func, *args, **kwargs):
             try:
                 return healer_func(*args, **kwargs)
             except Exception as e:
                 msg = f"⚠️ Non-Fatal Rule Fault in {healer_func.__qualname__}: {e}"
                 logger.warning(msg)
                 if hasattr(context, "audit_log"):
                     context.audit_log.append(msg)
                 return 0

        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_SELECTOR, state.context):
            modified += _safe_call(self.selector_healer.heal_docs, state.documents, state.identities, context=state.context)

        if BoundaryEnforcer.validate_mutation(self.permit, MutationScope.SPEC_PORTS, state.context):
            modified += _safe_call(self.port_healer.heal_docs, state.documents, state.identities, context=state.context)
        return modified
