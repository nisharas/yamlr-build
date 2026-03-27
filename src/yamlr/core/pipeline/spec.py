#!/usr/bin/env python3
"""
Yamlr STAGE SPECIFICATION
--------------------------
Immutable immutable descriptor for pipeline stages.
"""

from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass(frozen=True)
class StageSpec:
    """
    Immutable description of a pipeline stage.
    Why: To decouple stage configuration from execution, enabling 
         deterministic plan generation and serialization.
    """
    name: str
    stage_cls: Any  # Type[PipelineStage] or Callable
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    # Execution Flags
    # Why: Replaces string-fragility in the executor with explicit intent.
    abort_on_error: bool = False
    is_structural: bool = False

    # Governance & Reporting
    # Why: Enables data-driven license gating and categorical telemetry.
    pro_only: bool = False
    category: str = "core"  # structural, semantic, healing, risk, telemetry
