#!/usr/bin/env python3
"""
Yamlr Stage 10: Vacuum (Compact Mode)
--------------------------------------
Surgically removes blank lines from serialized YAML while preserving
content within block scalars (shards marked as is_block).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from yamlr.core.context import HealContext
from yamlr.core.stages.base import PipelineStage

logger = logging.getLogger("yamlr.pipeline.stages.vacuum")

class StageTenVacuum(PipelineStage):
    """
    The 'Compact Mode' Post-Processor.

    Why: Enterprises often require extremely dense YAML for CI environments 
         to reduce log noise. This stage provides that density without 
         breaking Kubernetes block scalars.
    """

    def __init__(self, name: str, enabled: bool = False):
        """
        Args:
            enabled: Whether to actually perform vacuuming.
        """
        super().__init__(name)
        self.enabled = enabled

    def run(self, context: HealContext) -> Dict[str, Any]:
        """
        Surgically removes blank lines from the serialized output.
        """
        if not self.enabled or not context.raw_text:
            return {}

        lines = context.raw_text.splitlines()
        result = []
        is_in_block = False
        block_indent = 0
        
        # We need a robust re-lex for block scalars in serialized output
        for line in lines:
            stripped = line.strip()
            
            # Detect block scalar entry (e.g., config: | # comment)
            # Allows | or > followed by optional chomp (+/-) and indent (\d)
            if re.search(r'[|>][+-]?\d?(\s*#.*|$)', stripped):
                is_in_block = True
                # The next non-blank line defines the block indentation
                block_indent = -1 
                result.append(line)
                continue

            if is_in_block:
                cur_indent = len(line) - len(line.lstrip())
                if stripped:
                    if block_indent == -1:
                        block_indent = cur_indent
                    
                    if cur_indent < block_indent:
                        is_in_block = False
                
            # If we are NOT in a block, and the line is empty, skip it.
            if not stripped and not is_in_block:
                continue
                
            result.append(line)
            
        original_count = len(lines)
        context.raw_text = "\n".join(result)
        vacuumed = original_count - len(result)
        
        if vacuumed > 0:
            context.audit_log.append(f"Stage 10: Vacuumed {vacuumed} blank lines (Compact Mode)")
        
        return {"vacuumed_count": vacuumed}
