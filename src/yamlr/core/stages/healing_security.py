"""
Yamlr Healing Stage - Security Hardening
--------------------------------------
What: Implements RBAC, Privilege Escalation, and Ingress security hardening.
Why: Security hardening is the primary driver for Yamlr Pro (VAL-02-1).
Where: Executed as part of the Healing Pipeline.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from yamlr.core.stages.base import PipelineStage, StageResult
from yamlr.healers.best_practices.rbac import RBACAuditor
from yamlr.healers.best_practices.privilege_escalation import PrivilegeEscalationAuditor
from yamlr.healers.best_practices.ingress import IngressAuditor
from yamlr.core.stages.boundaries import BoundaryEnforcer, HealerPermit, MutationScope

class HealingSecurityStage(PipelineStage):
    """
    Healing Security (RBAC & Privilege Escalation).
    
    Why: To encapsulate high-risk security mutations within a dedicated 
         audit-logged stage, ensuring 'Zero-Trust' in automated healing.
    """

    def __init__(self, harden: bool = False):
        super().__init__(name="HealingSecurity")
        self.rbac_auditor = RBACAuditor()
        self.pe_auditor = PrivilegeEscalationAuditor()
        self.ingress_auditor = IngressAuditor()
        self.harden = harden
        
        self.rbac_permit = HealerPermit("RBACAuditing", {MutationScope.SPEC_RBAC})
        self.pe_permit = HealerPermit("PrivilegeEscalation", {MutationScope.SPEC_SECURITY})
        self.ingress_permit = HealerPermit("IngressHardening", {MutationScope.SPEC_SECURITY, MutationScope.STRUCTURAL})

    def execute(self, state: PipelineState) -> StageResult:
        """
        Executes security hardening healing.
        
        Why: Enforces Pod Security Standards (PSS) and secures container runtimes.
        """
        modified_count = 0
        try:
            for doc in state.documents:
                modified_count += self._heal_single_doc_security(doc, doc, state.context)

            return StageResult(
                success=True,
                metadata={"modified": modified_count, "harden_active": self.harden}
            )
        except Exception as e:
            logger.error(f"HealingSecurityStage failed: {e}")
            return StageResult(success=False, errors=[str(e)])

    def _heal_single_doc_security(self, doc: Any, data: Any, context: Any) -> int:
        """Helper to process a single document's security hardening with Phase 14 Isolation."""
        modified = 0
        from yamlr.core.stages.healing_core import logger

        def _safe_call(healer_func, *args, **kwargs):
             try:
                 return healer_func(*args, **kwargs)
             except Exception as e:
                 msg = f"⚠️ Non-Fatal Security Rule Fault in {healer_func.__qualname__}: {e}"
                 logger.warning(msg)
                 if hasattr(context, "audit_log"):
                     context.audit_log.append(msg)
                 return False

        # 1. RBAC Auditing
        if _safe_call(self.rbac_auditor.heal_doc, data, context=context, harden=self.harden):
            if BoundaryEnforcer.validate_mutation(self.rbac_permit, MutationScope.SPEC_RBAC, context):
                modified += 1

        # 2. Privilege Escalation
        if _safe_call(self.pe_auditor.heal_doc, data, context=context, harden=self.harden):
            if BoundaryEnforcer.validate_mutation(self.pe_permit, MutationScope.SPEC_SECURITY, context):
                modified += 1

        # 3. Ingress Hardening
        if _safe_call(self.ingress_auditor.heal_doc, doc, context=context, harden=self.harden):
            if BoundaryEnforcer.validate_mutation(self.ingress_permit, MutationScope.SPEC_SECURITY, context):
                modified += 1
        return modified
