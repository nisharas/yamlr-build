#!/usr/bin/env python3
"""
Yamlr REMEDIATION STAGE
-----------------------
Executes automated repairs based on findings from external policy engines.

Why: Bridging external detection (OPA, Kyverno) with Yamlr's surgical healing.
     This stage closes the loop: Report -> Analysis -> Mutation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineStage
from yamlr.healers.best_practices.metadata import MetadataHealer
from yamlr.healers.best_practices.privilege_escalation import PrivilegeEscalationAuditor
from yamlr.healers.best_practices.resources import ResourcesHealer

logger = logging.getLogger("yamlr.pipeline.stages.remediation")
__all__ = ['StageExternalRemediation']


class StageExternalRemediation(PipelineStage):
    """
    Surgical stage that applies fixes for violations found by external adapters.
    """
    
    def __init__(self, name: str):
        super().__init__(name)
        self.security_healer = PrivilegeEscalationAuditor()
        self.metadata_healer = MetadataHealer()
        self.resource_healer = ResourcesHealer()

    def run(self, context: HealContext):
        """
        Iterates over findings and applies mapped mutations.
        """
        if not context.findings:
            logger.debug("Stage External Remediation: No findings to process.")
            return {"modified": 0}

        modified_indices = set()
        mutation_tracker = {} # Tracks which resource has been modified by which rule to prevent conflicts

        # We iterate over findings that have a fix_available and fix_id
        for finding in context.findings:
            if not finding.fix_available or not finding.fix_id:
                continue

            # [ANTI-RACE] Mutation Conflict Detection
            # A resource (kind/name) should ideally only be modified by one rule per stage
            field_key = f"{finding.resource_kind}:{finding.resource_name}"
            if field_key in mutation_tracker:
                prev_rule_id = mutation_tracker[field_key]
                logger.warning(f"Policy Conflict Detected! Resource '{field_key}' already modified by rule '{prev_rule_id}'. Skipping mutation for rule '{finding.rule_id}'.")
                continue
            
            # Mark this resource as being modified by the current finding's rule
            mutation_tracker[field_key] = finding.rule_id
            
            fix_id = finding.fix_id
            res_name = finding.resource_name
            res_kind = finding.resource_kind
            
            # Find the corresponding doc in context.docs
            # We iterate over all docs to find the matching one
            for i, doc in enumerate(context.docs or []):
                if not doc: continue
                
                # Access the underlying dictionary if it's a Document object, otherwise use directly
                doc_data = doc.data if hasattr(doc, 'data') else doc
                
                d_kind = doc_data.get("kind")
                d_metadata = doc_data.get("metadata") or {}
                d_name = d_metadata.get("name")
                
                logger.debug(f"Checking doc {i}: {d_kind}/{d_name}")
                
                if d_kind == res_kind and d_name == res_name:
                    logger.info(f"Matched finding for {res_kind}/{res_name} to doc {i}")
                    if self._apply_fix(doc, fix_id, context):
                        modified_indices.add(i)
                        logger.info(f"🛠️ Remediation Applied: {fix_id} to {res_kind}/{res_name}")
                    else:
                        logger.warning(f"Failed to apply fix {fix_id} to {res_kind}/{res_name}")

        return {"modified": len(modified_indices)}

    def _apply_fix(self, doc: Dict[str, Any], fix_id: str, context: HealContext) -> bool:
        """
        Dispatches fix_id to the specific healer logic.
        """
        # Map fix_id to healer methods
        if fix_id == "disallow_privileged":
            # [PRO-ATOMIC] We reuse existing healers as "Atomic Engines"
            return self.security_healer.heal_doc(doc, harden=True)
            
        elif fix_id == "inject_required_labels":
            # Attempt to get required labels from context/config, fallback to safe defaults
            # In a real enterprise scenario, these would come from the OPA/Kyverno parameters
            labels = {"yamlr-remediated": "true"}
            return self.metadata_healer.heal_labels(doc, required_labels=labels)
            
        elif fix_id == "enforce_namespace":
            return self.metadata_healer.heal_namespace(doc, default_namespace=context.default_namespace)

        elif fix_id == "enforce_resource_limits":
             return self.resource_healer.heal_doc(doc, enforce_defaults=True)
             
        elif fix_id == "enforce_readonly_root_fs":
            # Reuse SecurityContextHealer (it handles this during harden=True)
            return self.security_healer.heal_doc(doc, harden=True)
            
        elif fix_id == "enforce_non_root":
            return self.security_healer.heal_doc(doc, harden=True)

        elif fix_id == "fix_ingress_host":
            return self.metadata_healer.fix_ingress_host(doc)

        return False
