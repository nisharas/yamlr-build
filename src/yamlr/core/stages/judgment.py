#!/usr/bin/env python3
"""
Yamlr JUDGMENT STAGE - Phase 13 Truth Engine
--------------------------------------------
Final safety gate for manifest reconstruction.
Orchestrates KubeJudge to provide a definitive verdict.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-03-10
"""

from __future__ import annotations

import logging

from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineStage
from yamlr.validators.judge import KubeJudge

logger = logging.getLogger("yamlr.pipeline.stages.judgment")
__all__ = ["StageJudgment"]


class StageJudgment(PipelineStage):
    """
    Stage: Final Safety Judgment.
    ISSUES the definitive "Truth-in-Healing" verdict.
    """

    def __init__(self, name: str, catalog: dict, deep_check: bool = False):
        """
        Why: Decouples the High-Level Verdict engine from the low-level
             structural reconstruction.
        """
        super().__init__(name)
        self.judge = KubeJudge(catalog, deep_array_check=deep_check)

    def run(self, context: HealContext):
        """
        Executes the final safety gate.

        Saves 'verdict', 'trust_score', and 'detailed_safety_msgs'
        to the context.
        """
        if not context.docs:
            context.audit_log.append("  ⚠️ Stage Judgment: No documents found to judge.")
            return {"success": True, "trust_score": 0}

        # The Judge: Final Pre-flight Check
        # [PHASE-28] Optimized: Pass pre-calculated findings to skip re-validation
        valid, msgs, score = self.judge.judge_all(context.docs, pre_calculated=context.doc_findings)

        # [AUDIT-V15] Structural Integrity Bonus: Reward valid structure
        # If the manifest is basically valid (apiVersion/kind/name present), boost score.
        structural_bonus = 0
        if valid and not any("missing apiVersion" in m.lower() or "missing kind" in m.lower() for m in msgs):
            structural_bonus = 20.0
            context.audit_log.append(f"  ✨ Structural Integrity Bonus: +{structural_bonus} points")

        # Merged trust score logic: minimum of existing (security/risk) and new (judgment) + bonus
        current_score = getattr(context, "trust_score", 100.0)
        context.trust_score = min(100.0, min(float(current_score), float(score)) + structural_bonus)

        context.safety_verdict = "PASSED" if valid and context.trust_score > 70 else "CRITICAL"
        context.safety_messages = msgs

        # Inject into audit log
        verdict_icon = "✅" if valid else "❌"
        context.audit_log.append(f"Stage Judgment: {verdict_icon} Safety Verdict: {context.safety_verdict}")
        context.audit_log.append(f"  Confidence Score: {score}/100")

        for msg in msgs:
            context.audit_log.append(f"  - {msg}")

        return {"success": True, "valid": valid, "trust_score": score, "verdict": context.safety_verdict}
