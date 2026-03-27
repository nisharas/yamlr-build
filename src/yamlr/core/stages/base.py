#!/usr/bin/env python3
"""
Yamlr PIPELINE STAGE - The Procedural Base
------------------------------------------
Defines the base interface for all pipeline stages.
Each stage is responsible for a single transformation or analysis phase.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from yamlr.core.context import HealContext

__all__ = ['PipelineStage']


class PipelineStage(ABC):
    """
    Abstract Base Class for all pipeline healing stages.
    """

    def __init__(self, name: str):
        """Initializes the pipeline stage with a descriptive name.
        
        Why: To provide clear audit logs and execution path tracking.
        """
        self.name = name

    @abstractmethod
    def run(self, context: HealContext) -> Dict[str, Any]:
        """
        Executes the stage logic on the given context.
        
        Args:
            context: The active HealContext containing manifest state.
            
        Returns:
            Optional data or result produced by this stage.
        """
        pass
