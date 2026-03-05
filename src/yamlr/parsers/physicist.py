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

import logging
from typing import Any, List, Optional, Tuple, Type
from ruamel.yaml.comments import CommentedMap, CommentedSeq

logger = logging.getLogger("yamlr.parsers.physicist")

T_MAP = CommentedMap
T_SEQ = CommentedSeq

class IndentationPhysicist:
    """
    Manages the stack and state for rebuilding a YAML tree from shards.
    """

    def __init__(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        # [(indent: int, container: Map/Seq, parent_key: str, dot_path: str, item_indent: Optional[int])]
        self.stack = [(-1, T_MAP(), None, "", None)]

    def reset(self, root_container: T_MAP):
        """Resets the stack for a new document."""
        self.stack = [(-1, root_container, None, "", None)]

    def resolve_scope(self, shard_indent: int, is_list_item: bool, shard_key: Optional[str], schema_healer: Any):
        """
        Pops deeper scopes from the stack until the correct parent for the current shard is found.
        """
        while True:
            if len(self.stack) <= 1:
                break

            last_indent, last_cont, last_key, dot_path_top, item_indent = self.stack[-1]

            # If we are deeper, we are good (break)
            if shard_indent > last_indent:
                break

            # If same indent:
            if shard_indent == last_indent:
                # Special case: List items at the same indent
                if is_list_item:
                    # 1. If the current sequence already has items at a deeper level,
                    # then a same-indent shard MUST be a sibling of the sequence.
                    if (
                        isinstance(last_cont, T_SEQ)
                        and item_indent is not None
                        and shard_indent < item_indent
                    ):
                        self.stack.pop()
                        continue

                    # 2. If it's at the same level as a Map key, it's a sibling of the Map key.
                    if isinstance(last_cont, T_MAP) and last_indent != -1:
                        self.stack.pop()
                        continue

                    elif isinstance(last_cont, T_SEQ):
                        break

                # Sibling fields in a map inside a sequence
                keep_sibling = None

                # Case 1: Grandparent is a Seq (we are in an item map)
                if len(self.stack) > 1 and isinstance(self.stack[-2][1], T_SEQ):
                    keep_sibling = schema_healer.resolve_tri_state_ambiguity(
                        self.stack, shard_key, shard_indent
                    )

                # Case 2: Stack top is a Seq (we are same indent as the Seq marker)
                elif isinstance(self.stack[-1][1], T_SEQ) and not is_list_item:
                    if schema_healer.is_valid_sibling(dot_path_top, shard_key):
                        keep_sibling = True

                if keep_sibling:
                    break

            # If we are shallower (or same indent but not special case), pop
            if len(self.stack) > 1:
                self.stack.pop()
                continue
            else:
                break

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
