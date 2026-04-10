"""
Yamlr Normalization Stage
-------------------------
What: Reconstructs structured K8s models from raw YAML shards and captures layout.
Why: Centralizes the 'induct-to-struct' logic for all downstream analyzers.
Where: Executed as Stage 1 of the Yamlr Engine Pipeline.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from yamlr.core.stages.base import PipelineStage, StageResult, PipelineState

logger = logging.getLogger("yamlr.stages.normalization")

class NormalizationStage(PipelineStage):
    """
    Normalization Stage (Reconstruction).
    
    Why: To transform fragmented YAML tokens into a high-fidelity semantic graph
         that preserves comments and formatting using the Shadow engine.
    """

    def __init__(self):
        super().__init__(name="Normalization")

    def execute(self, state: PipelineState, engine: Optional[Any] = None) -> StageResult:
        """
        Reconstructs the YAML document from shards and shadow metadata.
        
        Why: To provide a high-fidelity Python model for analysis stages.
        """
        from yamlr.parsers.shadow import YamlrShadow
        
        # 1. Initialize Requisition (Share engine parser if available)
        if engine and hasattr(engine, "parser"):
            parser = engine.parser
            if state.context.compact:
                 parser.compact = True
        else:
            from yamlr.core.parser.ruamel_adapter import RuamelAdapter
            parser = RuamelAdapter(compact=state.context.compact)
            
        shadow = YamlrShadow()
        
        # 2. Capture and Graft Layout (Shadow Execution)
        # This ensures comments and gaps are anchored to semantic shards
        try:
            shadow.capture(state.content, state.shards)
            shadow.apply(state.shards)
        except Exception as e:
            logger.warning(f"Shadow capture degraded: {e}")
            # Non-fatal: Continue with raw reconstruction if shadow fails
        
        # 3. High-Fidelity Reconstruction
        try:
            docs = parser.load_all(state.content)
            state.documents = docs
            doc_count = len(docs)
            
            # [Phase 15] Memory Guardrail 1.0: Detect massive streams
            # Why: Prevents OOM in restricted memory environments by flagging pressure early.
            if doc_count > 100:
                logger.warning(
                    f"⚠️ MEMORY PRESSURE: Massive Stream detected ({doc_count} docs). "
                    "Rule execution and Shadow Grafting may experience latency or OOM. "
                    "Consider splitting manifests if instability occurs."
                )

            # [Iron Fortress] Optimization: We set the document count in metadata 
            # to help the ResourceGuard estimate memory pressure.
            return StageResult(
                success=True,
                metadata={"document_count": doc_count}
            )
        except Exception as e:
            logger.error(f"Normalization failed: {e}")
            return StageResult(success=False, errors=[str(e)])
