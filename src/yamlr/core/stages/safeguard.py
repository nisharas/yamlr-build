#!/usr/bin/env python3
"""
Stage 10.5: Agentic SafeGuard
-----------------------------
Emergency Brake for Autonomous Agents.
Prevents automated mutation of sensitive resources in SafeMode.
"""

from __future__ import annotations

import logging

from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineStage

logger = logging.getLogger("yamlr.stages.safeguard")

# Resources that require human approval or explicit --unsafe flag
SENSITIVE_KINDS = {"Secret", "ConfigMap", "Role", "RoleBinding", "ClusterRole", "ClusterRoleBinding", "CustomResourceDefinition"}

class StageAgenticSafeGuard(PipelineStage):
    """
    Blocks automation from touching sensitive resources unless explicitly permitted.
    """

    def __init__(self, name: str):
        super().__init__(name)

    def run(self, context: HealContext):
        """
        Why: To provide a 'Dead Man's Switch' for AI agents.
        If config.safe_mode is active, we block any mutation to sensitive resources.
        """
        if not context.config or not context.config.safe_mode:
            return {"success": True}

        # Detect any "FIX" or "HEAL" action taken by previous stages in prescriptions
        # HealAction objects have action_type, AnalysisResult objects (in findings) do not.
        has_mutated = any(p.action_type in ("fix", "heal", "repair", "harden") for p in context.prescriptions)

        if not has_mutated:
            return {"success": True}

        # Check if any sensitive resources were touched
        for identity in context.identities:
            if identity.kind in SENSITIVE_KINDS:
                # If we are in safe mode and haven't explicitly allowed unsafe actions
                if not context.config.allow_unsafe:
                    logger.warning(f"🛑 [SafeMode] Blocked mutation of sensitive {identity.kind}/{identity.name}")
                    
                    # Wipe the prescriptions for this file to effectively block the change
                    context.prescriptions = []
                    context.audit_log.append(f"🛑 [SafeMode] EMERGENCY BRAKE: Blocked mutation of {identity.kind}")
                    
                    return {
                        "success": False,
                        "error": f"SafeMode Block: Mutation of {identity.kind} is restricted for AI Agents.",
                        "status": "SAFE_MODE_BLOCK"
                    }

        return {"success": True}
