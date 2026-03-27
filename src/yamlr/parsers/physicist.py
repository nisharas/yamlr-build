#!/usr/bin/env python3
"""
Yamlr INDENTATION PHYSICIST
---------------------------
Handles the "physics" of YAML reconstruction:
- Stack-based scope management
- Indentation-based parent/child resolution
- List item sibling arbitration

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

from __future__ import annotations
import logging
from typing import Any, List, Optional, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
    pass

logger = logging.getLogger("yamlr.parsers.physicist")
__all__ = ['IndentationPhysicist']


class IndentationPhysicist:
    """
    Manages the stack and state for rebuilding a YAML tree from shards.
    """

    def __init__(self):
        """Initializes the indentation physicist.
        
        Why: To manage the stack-based state required for hierarchical YAML reconstruction.
        """
        # ROOT starts empty; initial container is set via reset()
        self.stack = []
        self.detected_indents: List[int] = []
        self._majority_indent: int = 2

    @property
    def majority_indent(self) -> int:
        """Returns the calculated dominant indentation step."""
        return self._majority_indent

    def track_indent(self, indent: int):
        """Records an indentation level seen in the manifest."""
        if indent > 0:
            self.detected_indents.append(indent)

    def calculate_majority_indent(self) -> int:
        """
        Derives the majority indentation step from collected data.
        
        Why: To support intelligent normalization during serialization.
        """
        if self.detected_indents:
            # find the most frequent non-zero indentation step
            diffs = [
                self.detected_indents[i] - self.detected_indents[i - 1]
                for i in range(1, len(self.detected_indents))
                if self.detected_indents[i] > self.detected_indents[i - 1]
            ]
            if diffs:
                self._majority_indent = max(set(diffs), key=diffs.count)
            else:
                self._majority_indent = (
                    min(self.detected_indents) if self.detected_indents else 2
                )
        return self._majority_indent

    def reset(self, root_container: Any):
        """Resets the stack and physics state for a new document."""
        self.stack = [(-1, root_container, None, "", None)]
        self.detected_indents = []
        self._majority_indent = 2

    def resolve_scope(self, shard_indent: int, is_list_item: bool, shard_key: Optional[str], schema_healer: Any, is_block: bool = False):
        """Adjusts the current scope based on the indentation of the incoming shard.
        
        Why: To ensure that YAML nodes are parented correctly according to their indentation levels. 
             Block scalar guards (is_block) prevent accidental scope popping within literal blocks.
        """
        if is_block:
            return  # Never pop scope while inside a block scalar shard stream

        while len(self.stack) > 1:
            last_indent, last_cont, last_key, _, item_indent = self.stack[-1]
            is_seq = hasattr(last_cont, "is_seq") and last_cont.is_seq

            if shard_indent > last_indent:
                break

            if shard_indent == last_indent:
                if self._should_keep_current_scope(is_seq, is_list_item, item_indent, shard_indent, last_cont, last_key, schema_healer, shard_key):
                    break

            logger.debug("Physics popping scope %s", last_key)
            self.stack.pop()

    def _should_keep_current_scope(self, is_seq: bool, is_list: bool, item_indent: Optional[int], s_indent: int, last_cont: Any, last_key: Optional[str], schema_healer: Any, shard_key: Optional[str]) -> bool:
        """Determines if the current stack top should be maintained for the existing shard."""
        is_map = hasattr(last_cont, "is_map") and last_cont.is_map

        # Standard YAML: A non-list-item at same indent as sequence marker is a sibling.
        if is_seq and not is_list:
            return False
            
        if is_list:
            if is_seq:
                if item_indent is not None and s_indent < item_indent:
                    return False
                return True
            if is_map:
                return False

        # If we are in an anonymous map (sequence item) and a KV pair arrives at 
        # the same indent, it belongs to this item (e.g. name/image in a container).
        if is_map and not is_list and last_key is None:
            return True
             
        # Default: yield to siblings
        return False

    def get_context(self) -> Tuple[int, Any, Optional[str], str, Optional[int]]:
        """Returns the current parent context."""
        return self.stack[-1]

    def push(self, indent: int, container: Any, key: Optional[str], dot_path: str, item_indent: Optional[int] = None):
        """Pushes a new scope onto the stack."""
        self.stack.append((indent, container, key, dot_path, item_indent))

    def update_item_indent(self, item_indent: int):
        """Updates the reference item indentation for the current sequence."""
        if self.stack:
            old = self.stack.pop()
            self.stack.append((old[0], old[1], old[2], old[3], item_indent))
