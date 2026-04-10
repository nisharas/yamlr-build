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
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

if TYPE_CHECKING:
    pass

logger = logging.getLogger("yamlr.parsers.physicist")
__all__ = ["IndentationPhysicist"]


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
                self._majority_indent = min(self.detected_indents) if self.detected_indents else 2
        return self._majority_indent

    def reset(self, root_container: Any):
        """Resets the stack and physics state for a new document."""
        self.stack = [(-1, root_container, None, "", None)]
        self.detected_indents = []
        self._majority_indent = 2

    def resolve_scope(self, shard_indent: int, is_list_item: bool, is_block: bool = False):
        """Adjusts the current scope based on the indentation of the incoming shard.

        Why: To ensure that YAML nodes are parented correctly according to their indentation levels.
             Block scalar guards (is_block) prevent accidental scope popping within literal blocks.
        """
        if is_block:
            return

        while len(self.stack) > 1:
            last_indent, last_cont, last_key, _, item_indent = self.stack[-1]
            is_seq = hasattr(last_cont, "is_seq") and last_cont.is_seq

            # [PHASE 24 GENESIS FIX] Hyper-Sticky Scoping: Check retention BEFORE aggressive popping.
            # This ensures siblings flush with the hyphen are NOT popped to root.
            if self._should_keep_current_scope(is_seq, is_list_item, item_indent, shard_indent, last_cont, last_key):
                break

            # [PHASE 32 OMEGA FIX] Sibling Retention:
            # If the shard is at the SAME indent as the last scope, we only pop
            # if we are explicitly leaving a specialized container.
            # Otherwise, we STAY and let the Structurer merge siblings.
            if shard_indent == last_indent:
                # [PHASE 33 REVELATION] Sibling Discrimination:
                # If this is a document root level key (indent 0) or a standard map,
                # we MUST pop to return to the parent container.
                # ONLY retain if we are in an anonymous item scope.
                if last_key is not None or shard_indent == 0:
                    pass  # Allow to fall through to pop
                else:
                    break  # Retention!

            if shard_indent > last_indent:
                break

            self.stack.pop()

            # [PHASE 18 FIX] Hard Stop: Never pop the root node (indent -1).
            if len(self.stack) <= 1:
                break

    def _should_keep_current_scope(
        self,
        is_seq: bool,
        is_list: bool,
        item_indent: Optional[int],
        s_indent: int,
        last_cont: Any,
        last_key: Optional[str],
    ) -> bool:
        """Determines if the current stack top should be maintained for the existing shard."""
        is_map = hasattr(last_cont, "is_map") and last_cont.is_map

        # [PHASE 28 OMEGA FIX] Sequence-Aware Scoping:
        # If the top of the stack is a sequence, and the shard is a sibling
        # of the sequence ITEMS (indent > p_indent), we MUST keep the scope
        # so the Structurer can merge it into the last item.
        if is_seq and not is_list:
            if s_indent > item_indent if item_indent is not None else s_indent > last_indent:
                return True
            return False

        if is_list:
            if is_seq:
                if item_indent is not None and s_indent < item_indent:
                    return False
                return True

        # [PHASE 22/27 REVELATION FIX] Hyper-Sticky Scoping: If we are in an
        # anonymous map (sequence item with no key), we claim all
        # siblings at 'item_indent' or deeper. This handles the 'image'
        # and 'http' jumble where they are flush with the hyphen.
        if is_map and last_key is None and item_indent is not None:
            if s_indent >= item_indent:
                return True
            # If less than item_indent, it's a sibling of the sequence.
            return False

        # [PHASE 23/25 REVELATION FIX] Retention for siblings at same indent in anonymous maps
        if is_map and not is_list and last_key is None:
            # Hyper-sticky check: Already handled above via item_indent comparison.
            # If we got here, just return False.
            return False

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
