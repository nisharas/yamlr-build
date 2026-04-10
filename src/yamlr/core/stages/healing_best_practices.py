"""
Yamlr Healing Stage - Best Practices
------------------------------------
What: Implements Image Tag pinning, Probes injection, Network Policies, and Namespace enforcement.
Why: Best practices improve cluster reliability and prevent non-deterministic rollouts.
Where: Executed as part of the Healing Pipeline.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from yamlr.core.stages.base import PipelineStage, StageResult
from yamlr.healers.best_practices.image_tag import ImageTagHealer

logger = logging.getLogger("yamlr.stages.best_practices")
from yamlr.healers.best_practices.probes import ProbeHealer
from yamlr.healers.best_practices.network_policy import NetworkPolicyHealer
from yamlr.healers.best_practices.namespace import NamespaceHealer
from yamlr.core.stages.boundaries import BoundaryEnforcer, HealerPermit, MutationScope

class HealingBestPracticesStage(PipelineStage):
    """
    Healing Best Practices (Reliability).
    
    Why: To ensure that workloads are following standardized reliability and 
         network segmentation practices within the cluster.
    """

    def __init__(self, fix_tags: bool = False, enforce_probes: bool = False, harden_net: bool = False, enforce_ns: bool = False):
        super().__init__(name="HealingBestPractices")
        self.image_healer = ImageTagHealer()
        self.probe_healer = ProbeHealer()
        self.network_healer = NetworkPolicyHealer()
        self.ns_healer = NamespaceHealer(enact=enforce_ns)
        
        self.fix_tags = fix_tags
        self.enforce_probes = enforce_probes
        self.harden_net = harden_net
        self.enforce_ns = enforce_ns

        self.image_permit = HealerPermit("ImageTagHealing", {MutationScope.SPEC_IMAGE})
        self.probe_permit = HealerPermit("ProbeInjection", {MutationScope.SPEC_PROBES})
        self.network_permit = HealerPermit("NetworkPolicyEnforcement", {MutationScope.SPEC_NETWORK})
        self.ns_permit = HealerPermit("NamespaceEnforcement", {MutationScope.SPEC_NAMESPACE})

    def execute(self, state: PipelineState, engine: Optional[Any] = None) -> StageResult:
        """
        Executes best practices healing logic.
        
        Why: Optimizes manifest for operational health (Probes, Tags, Network).
        """
        modified_count = 0
        try:
            # 1. Single-doc fixes (Probes, Tags)
            for doc in state.documents:
                modified_count += self._heal_single_doc_best_practices(doc, state.context)

            # 2. Multi-doc fixes (Network Policies)
            # Legacy healer expects list of docs and list of identities
            modified_count += self.network_healer.heal_docs(state.documents, state.identities, context=state.context)

            return StageResult(
                success=True,
                metadata={"modified": modified_count, "fix_tags": self.fix_tags}
            )
        except Exception as e:
            logger.error(f"HealingBestPracticesStage failed: {e}")
            return StageResult(success=False, errors=[str(e)])

    def _heal_single_doc_best_practices(self, doc: Any, context: Any) -> int:
        """Helper to process a single document's best practices code with Phase 14 Isolation."""
        modified = 0
        
        def _safe_call(healer_func, *args, **kwargs):
             try:
                 return healer_func(*args, **kwargs)
             except Exception as e:
                 msg = f"⚠️ Non-Fatal BestPractice Rule Fault in {healer_func.__qualname__}: {e}"
                 logger.warning(msg)
                 if hasattr(context, "audit_log"):
                     context.audit_log.append(msg)
                 return False

        # 1. Image Tag Pinning
        if BoundaryEnforcer.validate_mutation(self.image_permit, MutationScope.SPEC_IMAGE, context):
            if _safe_call(self.image_healer.heal_doc, doc, fix_latest=self.fix_tags, context=context):
                modified += 1

        # 2. Probe Injection
        if BoundaryEnforcer.validate_mutation(self.probe_permit, MutationScope.SPEC_PROBES, context):
            if _safe_call(self.probe_healer.heal_doc, doc, enforce_probes=self.enforce_probes, context=context):
                modified += 1
        return modified

    def _heal_multi_doc_best_practices(self, context: Any) -> int:
        """Helper to process multi-resource best practices with Isolation."""
        modified = 0
        
        def _safe_call(healer_func, *args, **kwargs):
             try:
                 return healer_func(*args, **kwargs)
             except Exception as e:
                 msg = f"⚠️ Non-Fatal BestPractice Rule Fault in {healer_func.__qualname__}: {e}"
                 logger.warning(msg)
                 if hasattr(context, "audit_log"):
                     context.audit_log.append(msg)
                 return 0

        if BoundaryEnforcer.validate_mutation(self.network_permit, MutationScope.SPEC_NETWORK, context):
            modified += _safe_call(self.network_healer.heal_docs, context.docs, context.identities, harden=self.harden_net, context=context)

        if self.enforce_ns and BoundaryEnforcer.validate_mutation(self.ns_permit, MutationScope.SPEC_NAMESPACE, context):
            _safe_call(self.ns_healer.heal_all, context)
            modified += len([m for m in context.audit_log if "Healed Namespace" in m])
        return modified
