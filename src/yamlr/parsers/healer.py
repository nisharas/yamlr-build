#!/usr/bin/env python3
"""
Yamlr Lexical Healer
--------------------
Contains heuristic and structural repair logic for raw YAML lines.
Extracted from YamlrLexer to comply with the Single Responsibility Principle.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from yamlr.models import Shard

logger = logging.getLogger("yamlr.healer")

class LexicalHealer:
    """
    Handles heuristic and context-aware repairs for YAML manifests.
    """

    SAFE_FUSED_KEYS = {
        "kind", "apiVersion", "metadata", "spec", "status", "selector",
        "template", "resources", "containers", "volumes", "labels",
        "annotations", "data", "ports", "env", "image"
    }

    def __init__(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.stats: Dict[str, int] = {
            "flush_left_lists_fixed": 0,
            "nested_lists_normalized": 0,
            "quote_repairs": 0,
            "spacing_fixes": 0,
            "floating_list_items_fixed": 0,
            "double_dash_normalized": 0,
        }
        self._last_list_parent_indent: Optional[int] = None
        self._consecutive_list_fixes: int = 0
        self._implicit_array_stack: List[Tuple[int, str]] = []  # [(indent, key)]
        self._implicit_array_item_active: bool = False
        self.heuristics: List[Any] = []
        self._init_heuristics()

    def _init_heuristics(self):
        """Initializes the heuristic strategy pipeline."""
        from .heuristics.indentation import (SnapToGridHeuristic,
                                             TabExpansionHeuristic)
        from .heuristics.punctuation import (MagicColonHeuristic,
                                             QuoteBalancingHeuristic,
                                             SpacingHeuristic)

        self.heuristics = [
            TabExpansionHeuristic(),
            SnapToGridHeuristic(),
            MagicColonHeuristic(),
            SpacingHeuristic(),
            QuoteBalancingHeuristic(),
        ]

    def reset_state(self):
        """Resets state for a new document."""
        self._last_list_parent_indent = None
        self._consecutive_list_fixes = 0
        self._implicit_array_stack.clear()
        self._implicit_array_item_active = False
        for k in self.stats:
            self.stats[k] = 0

    def heal_fused_keywords(self, line: str) -> str:
        """Fixes: 'kindService' -> 'kind: Service', etc."""
        stripped = line.strip()
        if not stripped or ":" in line or "[" in line or "{" in line:
            return line

        for key_candidate in self.SAFE_FUSED_KEYS:
            if stripped.startswith(key_candidate) and len(stripped) > len(key_candidate):
                suffix = stripped[len(key_candidate):]
                if suffix[0].isupper() or suffix[0].isdigit() or (key_candidate == "apiVersion" and suffix.lower().startswith("v")):
                    prefix_indent = len(line) - len(line.lstrip())
                    self.stats["spacing_fixes"] += 1
                    return (" " * prefix_indent) + f"{key_candidate}: {suffix}"
        return line

    def heal_double_dash(self, line: str) -> str:
        """Fixes: '- - key: val' -> '- key: val' and fragmented '--' markers."""
        stripped = line.lstrip()
        if stripped.startswith("- -"):
            indent = len(line) - len(stripped)
            self.stats["double_dash_normalized"] += 1
            return (" " * indent) + "- " + stripped[3:].lstrip()
        
        # [HEAL-1.2] Fragmentation: '--' or '-- ' at the start (common in legacy Helm)
        if stripped.startswith("--") and not stripped.startswith("---"):
            indent = len(line) - len(stripped)
            self.stats["double_dash_normalized"] += 1
            return (" " * indent) + "- " + stripped[2:].lstrip()
            
        return line

    def heal_missing_colon(self, line: str, next_line: Optional[str]) -> str:
        """Heals missing colon for parent keys based on next line indentation."""
        stripped = line.strip()
        if not stripped or ":" in stripped or "[" in stripped or "{" in stripped:
            return line

        if next_line:
            cur_indent = len(line) - len(line.lstrip())
            next_indent = len(next_line) - len(next_line.lstrip())
            # [HEAL-1.3] Aggressive Parent Detection
            # If next line is significantly deeper, assume this is a map parent
            if next_indent > cur_indent and next_line.strip():
                self.stats["spacing_fixes"] += 1
                return line.rstrip() + ":"
        return line

    def fix_flush_left_lists(self, shards: List[Shard], working_line: str) -> str:
        """Fixes list items that are flush-left but belong to a parent key."""
        if not shards:
            return working_line

        # [ROBUSTNESS FIX] Walk back to find the last structural shard
        # (ignoring comments and empty lines) to determine true parent indentation.
        last_structural_shard = None
        for i in range(len(shards) - 1, -1, -1):
            s = shards[i]
            if s.key or s.value or s.is_list_item:
                 last_structural_shard = s
                 break
        
        if not last_structural_shard:
            self._last_list_parent_indent = None
            self._consecutive_list_fixes = 0
            return working_line

        last_shard = last_structural_shard

        stripped = working_line.lstrip()
        current_indent = len(working_line) - len(stripped)
        if not stripped.startswith("-"):
            return working_line

        if current_indent > 0:
            expected_indent = last_shard.indent + 2
            if current_indent != expected_indent:
                working_line = (" " * expected_indent) + stripped
                self.stats["nested_lists_normalized"] += 1
            return working_line

        parent_indent = last_shard.indent
        expected_indent = parent_indent + 2
        if self._last_list_parent_indent == parent_indent:
            self._consecutive_list_fixes += 1
        else:
            self._last_list_parent_indent = parent_indent
            self._consecutive_list_fixes = 1

        self.stats["flush_left_lists_fixed"] += 1
        return (" " * expected_indent) + stripped

    def repair_line(self, line: str, in_block: bool) -> str:
        """Applies the main heuristic pipeline to a single line."""
        context = {"stats": self.stats, "in_block": in_block}
        for heuristic in self.heuristics:
            line = heuristic.apply(line, context)
        return line

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

            if shard.key and ":" in shard.raw_line:
                while context_stack and context_stack[-1][1] >= shard.indent:
                    context_stack.pop()
                if not shard.value:
                    context_stack.append((shard.key, shard.indent))
                normalized_shards.append(shard)
                i += 1
                continue

            if shard.is_list_item or shard.raw_line.lstrip().startswith("-"):
                expected_indent = context_stack[-1][1] + 2 if context_stack else 0
                if shard.indent != expected_indent:
                    shard.indent = expected_indent
                    shard.raw_line = (" " * expected_indent) + shard.raw_line.lstrip()
                    self.stats["nested_lists_normalized"] += 1

                j = i + 1
                while j < len(shards):
                    ns = shards[j]
                    if ns.is_doc_boundary or not (ns.is_list_item or ns.raw_line.lstrip().startswith("-")):
                        break
                    if ns.indent != expected_indent:
                        ns.indent = expected_indent
                        ns.raw_line = (" " * expected_indent) + ns.raw_line.lstrip()
                        self.stats["nested_lists_normalized"] += 1
                    j += 1
                normalized_shards.extend(shards[i:j])
                i = j
                continue

            normalized_shards.append(shard)
            i += 1
        return normalized_shards
