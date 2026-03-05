#!/usr/bin/env python3
"""
Yamlr PIPELINE STAGE - The Procedural Base
------------------------------------------
Defines the base interface for all pipeline stages.
Each stage is responsible for a single transformation or analysis phase.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from yamlr.core.context import HealContext

class PipelineStage(ABC):
    """
    Abstract Base Class for all pipeline healing stages.
    """

    def __init__(self, name: str):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.name = name

    @abstractmethod
    def run(self, context: HealContext) -> Any:
        """
        Executes the stage logic on the given context.
        
        Args:
            context: The active HealContext containing manifest state.
            
        Returns:
            Optional data or result produced by this stage.
        """
        pass
