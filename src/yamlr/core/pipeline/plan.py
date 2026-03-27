#!/usr/bin/env python3
"""
Yamlr PIPELINE PLAN
--------------------
Data-driven flight plan for manifest healing.
"""

from dataclasses import dataclass, field
from typing import Any, List
from .spec import StageSpec

@dataclass
class PipelinePlan:
    """
    An ordered sequence of StageSpecs defining a surgical workflow.
    Why: To provide a data-driven "Flight Plan" for the engine,
         eliminating hardcoded if/else chains in the orchestrator.
    """
    mode: str
    stages: List[StageSpec] = field(default_factory=list)

    @staticmethod
    def for_mode(mode: str, options: Any, pipeline: Any) -> "PipelinePlan":
        """
        [THE FLIGHT PLANNER]
        Generates an ordered sequence of stages based on the current mode and config.
        Why: Centralizes orchestration logic, eliminating "God Object" sprawl.
        """
        from yamlr.core.stages.registry import StageRegistry
        specs = StageRegistry.get_plan_specs(mode, options, pipeline)
        return PipelinePlan(mode=mode, stages=specs)
