#!/usr/bin/env python3
"""
Yamlr Lexical Healer
--------------------
Contains heuristic and structural repair logic for raw YAML lines.
Extracted from YamlrLexer to comply with the Single Responsibility Principle.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from yamlr.core.forensics import ForensicLogger
from yamlr.models import K8S_CORE_KEYS, Shard

logger = logging.getLogger("yamlr.healer")
__all__ = ["LexicalHealer"]


class LexicalHealer:
    """
    Handles heuristic and context-aware repairs for YAML manifests.

    Note: TableContinuationHeuristic remains outside the main heuristic pipeline
    as it requires access to the full Shard sequence for context-aware
    lookbehind, which exceeds the line-by-line scope of other heuristics.
    """

    SAFE_FUSED_KEYS = K8S_CORE_KEYS

    def __init__(self):
        """Initializes the lexical healer with a suite of heuristics.

        Why: To enable automated, line-level structural repairs of malformed YAML manifests.
        """
        self.stats: Dict[str, int] = {
            "flush_left_lists_fixed": 0,
            "nested_lists_normalized": 0,
            "quote_repairs": 0,
            "spacing_fixes": 0,
            "floating_list_items_fixed": 0,
            "double_dash_normalized": 0,
        }
        self._implicit_array_stack: List[Tuple[int, str]] = []  # [(indent, key)]
        self._implicit_array_item_active: bool = False
        self.heuristics: List[Any] = []
        self.debug_forensics: bool = False
        self._init_heuristics()

    def _init_heuristics(self):
        """Initializes the heuristic strategy pipeline."""
        from .heuristics.boolean_guard import BooleanGuardHeuristic
        from .heuristics.flow_sanitizer import FlowStyleHeuristic
        from .heuristics.indentation import SnapToGridHeuristic, TabExpansionHeuristic
        from .heuristics.keywords import KeywordFusionHeuristic, MissingColonHeuristic
        from .heuristics.legacy import LegacyMarkerHeuristic
        from .heuristics.list_indentation import ListIndentationHeuristic
        from .heuristics.punctuation import MagicColonHeuristic, QuoteBalancingHeuristic, SpacingHeuristic
        from .heuristics.sequence import FragmentedSequenceHeuristic
        from .heuristics.template_safety import TemplateSafetyHeuristic

        self.heuristics = [
            TemplateSafetyHeuristic(),
            TabExpansionHeuristic(),
            ListIndentationHeuristic(),
            SnapToGridHeuristic(),
            FragmentedSequenceHeuristic(),
            KeywordFusionHeuristic(),
            MissingColonHeuristic(),
            MagicColonHeuristic(),
            SpacingHeuristic(),
            QuoteBalancingHeuristic(),
            BooleanGuardHeuristic(),
            FlowStyleHeuristic(),
            LegacyMarkerHeuristic(),
        ]

    def reset_state(self):
        """Resets state for a new document."""
        self._implicit_array_stack.clear()
        self._implicit_array_item_active = False
        for k in self.stats:
            self.stats[k] = 0

    def repair_line(
        self, line: str, in_block: bool, shards: List[Shard] = None, next_line: str = None
    ) -> Tuple[str, List[str]]:
        """Applies the main heuristic pipeline to a single line.
        Returns: (repaired_line, list_of_intent_tags)
        """
        context = {
            "stats": self.stats,
            "in_block": in_block,
            "shards": shards or [],
            "next_line": next_line,
            "pending_tags": [],
        }
        for heuristic in self.heuristics:
            line = heuristic.apply(line, context)
        return line, context["pending_tags"]

    def normalize_indentation(self, shards: List[Shard]) -> List[Shard]:
        """Phase 2: Context-aware indentation normalization."""
        if not shards:
            return shards

        context_stack: List[Tuple[str, int]] = []
        normalized_shards = []

        i = 0
        while i < len(shards):
            shard = shards[i]
            if shard.is_doc_boundary:
                context_stack.clear()
                normalized_shards.append(shard)
                i += 1
                continue

            if shard.is_list_item or shard.raw_line.lstrip().startswith("-"):
                group, next_idx = self._normalize_list_group(shards, i, context_stack)
                normalized_shards.extend(group)
                i = next_idx
                continue

            if shard.key and ":" in shard.raw_line:
                self._update_context_stack(context_stack, shard)
                normalized_shards.append(shard)
                i += 1
                continue

            normalized_shards.append(shard)
            i += 1
        return normalized_shards

    def _update_context_stack(self, stack: List[Tuple[str, int]], shard: Shard) -> None:
        """Updates the indentation context stack based on the current key."""
        while stack and stack[-1][1] >= shard.indent:
            stack.pop()
        if not shard.value:
            stack.append((shard.key, shard.indent))

    def _normalize_list_group(
        self, shards: List[Shard], start_idx: int, stack: List[Tuple[str, int]]
    ) -> Tuple[List[Shard], int]:
        """Normalizes an entire group of list items to the same indentation."""
        expected_indent = stack[-1][1] + 2 if stack else 0
        ForensicLogger.log(
            "healer_debug.log",
            f"DEBUG: normalize start_idx={start_idx} stack_len={len(stack)} expected={expected_indent}",
            enabled=self.debug_forensics,
        )
        if stack:
            ForensicLogger.log("healer_debug.log", f"DEBUG: stack_top={stack[-1]}", enabled=self.debug_forensics)
        group = []
        i = start_idx

        while i < len(shards):
            shard = shards[i]
            if shard.is_doc_boundary or not (shard.is_list_item or shard.raw_line.lstrip().startswith("-")):
                break

            if shard.indent != expected_indent:
                shard.indent = expected_indent
                shard.raw_line = (" " * expected_indent) + shard.raw_line.lstrip()
                self.stats["nested_lists_normalized"] += 1

            group.append(shard)
            i += 1

        return group, i
