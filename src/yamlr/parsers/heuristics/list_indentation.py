from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from yamlr.models import Shard
from .base import BaseHeuristic

logger = logging.getLogger("yamlr.lexer.heuristics")
__all__ = ['ListIndentationHeuristic']


class ListIndentationHeuristic(BaseHeuristic):
    """
    Enforces structural list indentation rules.
    
    Why: LEGACY AUDIT V3. Fixes 'flush-left' lists that belong to a parent 
         and 'floating' items that don't align with the 2-space grid.
    """

    def __init__(self):
        self._last_list_parent_indent: Optional[int] = None

    @property
    def name(self) -> str:
        return "list_indentation"

    @property
    def description(self) -> str:
        return "Heals flush-left or misaligned list indicators"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """
        Adjusts indentation for sequence items.
        """
        if context.get("in_block", False):
            return line

        shards: List[Shard] = context.get("shards", [])
        stripped = line.lstrip()
        if not stripped.startswith("-") or stripped.startswith("---"):
            return line

        current_indent = len(line) - len(stripped)
        
        # [HEAL] Find last structural parent
        last_shard = None
        for i in range(len(shards) - 1, -1, -1):
            s = shards[i]
            if not s.is_doc_boundary and (s.key or s.value or s.is_list_item):
                last_shard = s
                break

        if not last_shard:
            return line

        parent_indent = last_shard.indent
        
        # 1. Flush-Left Recovery: "- item" at 0 but parent is at N
        if current_indent == 0 and parent_indent >= 0:
            expected_indent = parent_indent + 2
            if "stats" in context:
                context["stats"]["flush_left_lists_fixed"] = context["stats"].get("flush_left_lists_fixed", 0) + 1
            return (" " * expected_indent) + stripped

        # 2. Grid Misalignment: Indent 3/5/7 etc
        if current_indent > 0 and current_indent % 2 != 0:
            # Snap to parent+2 if close, otherwise nearest grid
            expected_indent = parent_indent + 2
            if abs(current_indent - expected_indent) <= 1:
                final_indent = expected_indent
            else:
                final_indent = current_indent + 1 # Round up to even
            
            if "stats" in context:
                context["stats"]["nested_lists_normalized"] = context["stats"].get("nested_lists_normalized", 0) + 1
                context["stats"]["floating_list_items_fixed"] = context["stats"].get("floating_list_items_fixed", 0) + 1
            return (" " * final_indent) + stripped

        return line
