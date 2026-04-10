#!/usr/bin/env python3
"""
Table-Style Continuation Heuristic
----------------------------------
Detects multi-line list entries that lack the '-' marker on subsequent lines.
Ported from legacy KubeCuro for high-gravity healing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from yamlr.models import Shard


class TableContinuationHeuristic:
    """
    The 'Row Binder': Connects fragmented list lines.

    Why: In corrupted manifests, lists often break indentation or lose bullets.
         This heuristic ensures they remain grouped as a single logical entry.
    """

    @staticmethod
    def is_continuation(previous_shards: List[Shard], indent: int, is_list: bool, is_doc: bool) -> bool:
        """
        Determines if the current line is a continuation of the previous list item.

        Args:
            previous_shards: The list of shards already processed.
            indent: Indentation level of the current line.
            is_list: Whether the current line started with a '-' bullet.
            is_doc: Whether the current line is a document boundary ('---').

        Returns:
            True if this is a table-style continuation.
        """
        if is_list or is_doc or not previous_shards:
            return False

        last_shard = previous_shards[-1]

        # Heuristic: Previous was a list item, current has identical indent,
        # but current lacks its own bullet. This is often a "Table Row"
        # in legacy ConfigMaps.
        return last_shard.is_list_item and indent == last_shard.indent
