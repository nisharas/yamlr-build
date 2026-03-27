#!/usr/bin/env python3
"""
RISK STAGE - The Safety Officer
------------------------------
Evaluates security posture and stability risks of the manifest.

### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-03-20: Security Scoring Integration**
   - **Context**: Users needed a "Safety Verdict" before applying automated repairs.
   - **Decision**: Integrate `ScoringEngine` to produce a high-fidelity risk profile.
   - **Consequence**: Enabled the "Safe/Warning/Critical" triage in `yamlr status`.

2. **2026-03-24: HostPath Security Lockdown**
   - **Context**: Absolute hostPath mounts are a major security backdoor.
   - **Decision**: Implement aggressive `hostPath` validation in this stage.
   - **Consequence**: M&A readiness improved by catching high-risk configuration patterns.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from yamlr.analyzers.risk_classifier import RiskClassifier
from yamlr.core.context import HealContext
from yamlr.core.resource_graph import ResourceGraph
from yamlr.core.stages.base import PipelineStage

logger = logging.getLogger("yamlr.pipeline.stages.risk")
__all__ = ['StageTenRiskClassification']


class StageTenRiskClassification(PipelineStage):
    """Stage 10: Human-Centric Risk Classification."""
    
    def __init__(self, name: str):
        """
        Why: Decouples risk logic from specific analyzers to ensure 
             consistent scoring across the entire findings collection.
        """
        super().__init__(name)
        self.classifier = RiskClassifier()
        try:
            from yamlr.pro.shield import ShieldEngine
            self.shield = ShieldEngine()
        except ImportError:
            self.shield = None

    def run(self, context: HealContext) -> Dict[str, Any]:
        """
        Why: Final pass over all findings to apply impact heuristics.
        """
        if not context.findings:
            return {"findings_enriched": 0}

        # 1. Build/Update Resource Graph if missing (Stage 3.5 usually does this, 
        # but we ensure it here for robustness).
        if not context.resource_graph:
            context.resource_graph = ResourceGraph()
            context.resource_graph.build(context.identities)

        # 2. Enrich each finding
        enriched_count = 0
        for finding in context.findings:
            try:
                self.classifier.enrich_finding(finding, context.resource_graph)
                enriched_count += 1
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                logger.warning(f"Could not classify risk for finding: {e}")

        # 3. Enterprise Shadow Risk Detection
        if self.shield:
            self._apply_enterprise_risks(context)

        context.audit_log.append(f"Stage 10: Risk classification complete ({enriched_count} findings enriched)")
        return {"findings_enriched": enriched_count}

    def _apply_enterprise_risks(self, context: HealContext):
        """Helper to run ShieldEngine risk detection and trust scoring."""
        for identity in context.identities:
            if hasattr(identity, "doc_index") and identity.doc_index < len(context.docs):
                doc_obj = context.docs[identity.doc_index]
                shadow_findings = self.shield.detect_shadow_risks(doc_obj, graph=context.resource_graph)
                if shadow_findings:
                    context.findings.extend(shadow_findings)

        total_risk = sum(1.0 for f in context.findings if f.risk_level == "HIGH")
        new_score = self.shield.calculate_trust_score(context, finding_risk_total=total_risk)
        context.trust_score = min(float(getattr(context, "trust_score", 100.0)), float(new_score))
        context.audit_log.append(f"🛡️ Shield Engine: Trust Score calculated: {context.trust_score:.1f}%")


class StageSecurityScoring(PipelineStage):
    """
    Stage 7.5: Security Hardening & Penalty Injection.
    Runs after reconstruction but before final serialization to avoid double-parsing.
    """
    def __init__(self, name: str, allowed_host_paths: Optional[List[str]] = None):
        super().__init__(name)
        from yamlr.core.engine.security import HardeningEngine
        self.engine = HardeningEngine(allowed_host_paths)

    def run(self, context: HealContext) -> Dict[str, Any]:
        """
        Scans context.docs for risky configurations and applies DNA Integrity penalties.
        """
        context.audit_log.append(f"Stage 7.5: Security Scoring running for {context.file_path}")
        penalty = self.engine.apply_penalties_to_context(context)
        return {"penalty": penalty, "security_findings": len(context.findings)}
