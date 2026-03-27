#!/usr/bin/env python3
"""
Yamlr EXTRACTION STAGES - Stages 0-3
-----------------------------------
Implements the initialization and extraction phases of the pipeline.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from yamlr.parsers.lexer import YamlrLexer
    from yamlr.parsers.shadow import ShadowEngine
from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineStage
from yamlr.core.stages.boundaries import MutationScope
from yamlr.models import HealAction, Shard

logger = logging.getLogger("yamlr.pipeline.stages.extraction")
from yamlr.core.stages.identity import IdentityStage as StageThreeIdentityExtraction

__all__ = ['StageZeroReset', 'StageOneLexicalRepair', 'StageTwoLayoutCapture', 'StageThreeIdentityExtraction']


class StageZeroReset(PipelineStage):
    """Stage 0: Internal pipeline state reset."""
    def __init__(self, name: str, shadow: "ShadowEngine"):
        """Initializes the reset stage with the shadow engine.
        
        Why: To ensure a clean state before each healing pipeline execution.
        """
        super().__init__(name)
        self.shadow = shadow

    def run(self, context: HealContext):
        """Resets the internal shadow engine state.
        
        Why: To prevent state leakage between independent healing runs.
        """
        self.shadow.reset()
        context.audit_log.append("Stage 0: Internal pipeline state reset")
        return {"success": True}

class StageOneLexicalRepair(PipelineStage):
    """Stage 1: Lexical repair and sharding."""
    def __init__(self, name: str, lexer: "YamlrLexer"):
        """Initializes the lexical repair stage.
        """
        super().__init__(name)
        self.lexer = lexer

    def run(self, context: HealContext):
        """Executes lexical repair and shards the raw input text.
        
        Why: To transform messy raw YAML into manageable, repairable fragments.
        """
        try:
            shards: List[Shard] = self.lexer.shard(context.raw_text)
            context.shards = shards
            context.audit_log.append(f"Stage 1: Lexer produced {len(shards)} shards")

            lexer_repairs = self.lexer.get_repair_audit_log()
            if lexer_repairs:
                context.audit_log.append("Stage 1: Lexer Healing Summary:")
                for entry in lexer_repairs:
                    context.prescribe(HealAction(
                        stage="Lexer",
                        action_type="repair",
                        target="lexical",
                        description=entry,
                        severity="INFO",
                        scope=MutationScope.STRUCTURAL
                    ))
            else:
                context.audit_log.append("Stage 1: No lexical repairs needed (clean YAML)")

            return {
                "success": True, 
                "shards": shards,
                "stats": {
                    "lexer_repairs": sum(self.lexer.repair_stats.values())
                }
            }
        except Exception as e:
            import traceback
            logger.error(f"Lexer critical failure: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

class StageTwoLayoutCapture(PipelineStage):
    """Stage 2: Layout and comment capture."""
    def __init__(self, name: str, shadow: "ShadowEngine"):
        """Initializes the layout capture stage with the shadow engine.
        """
        super().__init__(name)
        self.shadow = shadow

    def run(self, context: HealContext):
        """Captures layout and comment metadata from the raw text.
        
        Why: To ensure that healing remains comment-preserving and deterministic.
        """
        try:
            self.shadow.capture(context.raw_text, context.shards)
            self.shadow.apply(context.shards)
            context.audit_log.append("Stage 2: Layout and comment metadata generated")
            return {"success": True}
        except (AttributeError, KeyError, IndexError, ValueError) as e:
            context.audit_log.append(f"Stage 2: Warning - Layout preservation limited: {e}")
            return {"success": True, "warning": str(e)}
