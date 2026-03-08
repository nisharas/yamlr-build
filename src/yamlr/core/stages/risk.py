#!/usr/bin/env python3
"""
Yamlr RISK CLASSIFICATION STAGE - Stage 10
------------------------------------------
Enriches analysis findings with heuristic risk levels and impact descriptions.

Why: Transforms raw findings into actionable safety intelligence. 
     Uses the ResourceGraph to calculate blast-radius and impact scope.
"""

import logging
from typing import List, Dict, Any, Optional

from yamlr.core.stages.base import PipelineStage
from yamlr.core.context import HealContext
from yamlr.analyzers.risk_classifier import RiskClassifier
from yamlr.core.resource_graph import ResourceGraph
from yamlr.pro.shield import ShieldEngine

logger = logging.getLogger("yamlr.pipeline.stages.risk")

class StageTenRiskClassification(PipelineStage):
    """Stage 10: Human-Centric Risk Classification."""
    
    def __init__(self):
        """
        Why: Decouples risk logic from specific analyzers to ensure 
             consistent scoring across the entire findings collection.
        """
        super().__init__("Stage 10: Risk Classification")
        self.classifier = RiskClassifier()
        self.shield = ShieldEngine()

    def run(self, context: HealContext):
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
            # We use duck-typing / in-place modification for AnalysisResult
            try:
                self.classifier.enrich_finding(finding, context.resource_graph)
                enriched_count += 1
            except Exception as e:
                logger.warning(f"Could not classify risk for finding: {e}")

        # Enterprise Shadow Risk Detection (Zero-Blindspot fix)
        for identity in context.identities:
            if hasattr(identity, "doc_index") and identity.doc_index < len(context.docs):
                doc_obj = context.docs[identity.doc_index]
                shadow_findings = self.shield.detect_shadow_risks(doc_obj)
                if shadow_findings:
                    context.findings.extend(shadow_findings)

        context.audit_log.append(f"Stage 10: Risk classification complete ({enriched_count} findings enriched)")
        return {"findings_enriched": enriched_count}
