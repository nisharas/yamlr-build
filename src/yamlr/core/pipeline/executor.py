#!/usr/bin/env python3
"""
Yamlr PIPELINE EXECUTOR
-----------------------
The surgical hands that execute a PipelinePlan.
"""

import logging
import time
from typing import Any, Dict, List
from .spec import StageSpec
from .plan import PipelinePlan
from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineStage
from yamlr.models import PipelineStats

logger = logging.getLogger("yamlr.pipeline.executor")

class PipelineExecutor:
    """
    [THE SURGEON'S HANDS]
    Executes a PipelinePlan by iterating through stages and applying mutations.
    Why: Decouples "How to run" (error handling, logging, timings) from 
         "What to run" (the plan).
    """

    def __init__(self, plan: PipelinePlan):
        self.plan = plan
        self._instantiated_stages: List[PipelineStage] = []

    def execute(self, context: HealContext) -> Dict[str, Any]:
        """Runs the entire plan on the provided context."""
        results = {}
        for spec in self.plan.stages:
            if not spec.enabled:
                logger.debug(f"SKIPPING DISABLED STAGE: {spec.name}")
                continue

            stage = self._instantiate_stage(spec)
            cls_name = stage.__class__.__name__
            logger.debug(f"EXECUTING STAGE: {spec.name} [{cls_name}]")
            
            start_time = time.time()
            try:
                stage_output = stage.run(context)
                results[spec.name] = stage_output
                
                # [TELEMETRY] Aggregate stage stats
                if isinstance(stage_output, dict):
                    self._update_stats(context.stats, stage, stage_output)
                    
                duration = time.time() - start_time
                context.audit_log.append(f"Stage '{spec.name}' completed in {duration:.4f}s")
            except Exception as e:
                logger.exception(f"Stage '{spec.name}' failed with exception.")
                context.audit_log.append(f"CRITICAL: Stage '{spec.name}' failed: {e}")
                results[spec.name] = {"error": str(e), "success": False}
                
                # [POLICY] Abort if explicitly flagged as a structural/critical failure.
                if spec.abort_on_error:
                    logger.critical(f"ABORTING PIPELINE: Critical Stage '{spec.name}' failed.")
                    break

        return results

    def _update_stats(self, stats: PipelineStats, stage: PipelineStage, output: Dict[str, Any]):
        """Aggregates telemetry from stage results into global stats."""
        from yamlr.core.engine.result_aggregator import ResultAggregator
        ResultAggregator.collect_stage_stats(stage, output, stats)

    def _instantiate_stage(self, spec: StageSpec) -> PipelineStage:
        """Lazy instantiation of stage classes or factories."""
        if callable(spec.stage_cls):
            return spec.stage_cls(name=spec.name, **spec.config)
        return spec.stage_cls  # Likely already instantiated object
