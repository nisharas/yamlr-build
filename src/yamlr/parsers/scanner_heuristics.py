#!/usr/bin/env python3
"""
Scanner HEURISTICS Mixin
------------------------
Intent tagging, path tracking, repair correlation, and metadata extraction.

Why: Extracted from scanner.py to enforce the <500 line modularity rule.
This mixin provides all heuristic/analysis methods that YamlrScanner inherits.

Architecture: Mixin pattern — shares state via `self` with the main class.
All methods are private (_prefixed) and called only by YamlrScanner internals.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-17
"""

from __future__ import annotations

import logging
from typing import Any

from yamlr.models import SPECIAL_PURPOSE_BLOCKS, Shard
from yamlr.parsers.metadata_extractors import get_extractors

logger = logging.getLogger("yamlr.scanner")
__all__ = ["HeuristicsMixin"]


class HeuristicsMixin:
    """
    Heuristic analysis methods for YamlrScanner.

    Responsibilities:
    - Semantic intent tagging (tri-tier system)
    - Repair correlation with Lexer metadata
    - Indentation Physics path tracking
    - Cross-resource metadata extraction
    - DNA sanitization
    """

    # =========================================================================
    # ENHANCED INTENT TAGGING & HEURISTICS
    # =========================================================================

    def _tag_intent(self, shard: Shard, key: str) -> None:
        """
        Tags shards with semantic intent for downstream confidence scoring.

        Heuristic Algorithm:
        The archeologist uses a tri-tier tagging system to label manifestations:

        1. Structural Recognition: Does the key match the K8s core catalog?
           (e.g., 'spec', 'metadata', 'containers').

        2. Indentation Physics: Where does the key sit in the hierarchy?
           - Level 1: Root Field (High Identification Potential)
           - Level 2: Nested Field (Standard Context)
           - Level 3+: Deep Field (Low Identity Relevance)

        3. Repair Correlation: Was this line healed by the Stage 1 Lexer?
           If so, it is tagged as '.repaired' to adjust the overall confidence
           score of the manifest. This allows the Pipeline to penalize the
           confidence of "heavily healed" documents.

        Args:
            shard: The shard object being evaluated.
            key: Normalized key name after stripping whitespace/quotes.
        """
        # Safety Check: Do not overwrite tags set by identity extraction logic.
        if hasattr(shard, "intent_tag") and shard.intent_tag:
            return

        # Tier 1: Unified Catalog Matching (Known World)
        if key in self._known_structure_keys:
            shard.intent_tag = f"k8s.{key}"
            return

        # Tier 2: Indentation Physics (Relative Context)
        path_depth = len(self._path_stack)
        if path_depth == 1:
            shard.intent_tag = "k8s.root_field"
        elif path_depth == 2:
            shard.intent_tag = "k8s.nested_field"
        elif path_depth >= 3:
            shard.intent_tag = "k8s.deep_field"

        # Tier 3: Repair Correlation (Forensic Audit)
        if self._lexer_context and self._was_repaired(shard):
            # Annotate tag to signal this line was healed before identification.
            existing_tag = shard.intent_tag or "unknown"
            shard.intent_tag = f"{existing_tag}.repaired"

    def _was_repaired(self, shard: Shard) -> bool:
        """
        Determines if a specific Shard correlates to a Lexer repair marker.

        Heuristic Strategy:
        We compare shard properties against the lexer's repair histogram.
        Note: This currently uses broad heuristics; future versions will
        use line-specific repair IDs to ensure 1:1 correlation in large files.

        Returns:
            bool: True if the shard's line was likely modified by structural healing.
        """
        if not self._lexer_context:
            return False

        # [PRECISION-10] Use line-specific repair tags if available
        # Why: Global repair_stats (flush_left_lists_fixed) can cause false positives
        # for all list items in a large file. intent_tag ensures 1:1 correlation.
        if hasattr(shard, "intent_tag") and shard.intent_tag:
            tag_lower = (shard.intent_tag or "").lower()
            if any(marker in tag_lower for marker in ["repaired", "fixed", "normalized", "typo"]):
                return True

        repair_stats = self._lexer_context.get("repair_stats", {})

        # Check 1: List item indentation corrections.
        if shard.is_list_item and repair_stats.get("flush_left_lists_fixed", 0) > 0:
            return True

        # Check 2: Quote/Value literal healing.
        if shard.value and repair_stats.get("quote_repairs", 0) > 0:
            return True

        # Check 3: Spacing and colon insertion.
        if shard.key and repair_stats.get("spacing_fixes", 0) > 0:
            return True

        return False

    def _has_schema_for(self, kind: str) -> bool:
        """
        Verification method to check if a schema definition exists for a Kind.

        This delegates lookup to the SchemaManager which aggregates
        core schemas, CRDs, and OpenAPI plugins into a unified search space.
        """
        return self.schema_manager.has_schema_for(kind)

    # =========================================================================
    # PATH CONTEXT & INDENTATION PHYSICS
    # =========================================================================

    def _update_path_context(self, shard: Shard) -> None:
        """
        Uses 'Indentation Physics' to track the current key hierarchy.

        Mechanism:
        The scanner maintains a "Vertical Stack" of (indent, key) tuples.
        This is a non-recursive way to understand the document's structure
        without a full parse tree.

        Logic Rules:
        1. Deeper: If current indent > stack top, we are moving into a sub-block.
        2. Sibling: If current indent == stack top, we are moving horizontally.
        3. Outer: If current indent < stack top, we pop until we find a match.

        Ambiguity Solving:
        This prevents 'metadata.name' from misidentifying a Pod inside a
        Deployment. Only the root 'metadata' block qualifies as the
        "Global Identity" of the resource. Detailed tracking of recursion
        depth is essential for handling complex manifests like Helm templates.

        Args:
            shard: The current shard being processed.
        """
        # Rule of Physics: Pop all deeper scopes that we have exited.
        while self._path_stack and self._path_stack[-1][0] >= shard.indent:
            self._path_stack.pop()

        # Rule of Logic: Update hierarchy with the current key.
        if shard.key:
            self._path_stack.append((shard.indent, shard.key))

        # Context Analysis: Build the current dot-path keys.
        path_keys = [pk for (_, pk) in self._path_stack]

        # Freeform Block Detection:
        # Blocks like 'labels' or 'data' can contain arbitrary keys.
        # We disable fuzzy matching in these areas to prevent false positives
        # (e.g., matching a label 'kind: prod' as the resource Kind).
        # Fixes Finding 28.1 (Audit Round 28) - Centralized Source of Truth.
        self._in_freeform_block = any(k in path_keys for k in SPECIAL_PURPOSE_BLOCKS)

        # Global Metadata Enforcement:
        # We strictly define 'Global Metadata' as the 'metadata' block that
        # sits at the absolute root of the document (Stack Index 0).
        if "metadata" in path_keys:
            try:
                metadata_index = path_keys.index("metadata")
                # Must be at root or directly under root for multi-doc alignment.
                self._in_global_metadata = metadata_index == 0
            except (ValueError, IndexError):
                self._in_global_metadata = False
        else:
            self._in_global_metadata = False

    # =========================================================================
    # METADATA EXTRACTION (GRAPH DNA)
    # =========================================================================

    def _extract_cross_resource_metadata(self, shard: Shard, key: str, val: str) -> None:
        """
        Invokes metadata extractors to build the manifest set graph.

        Extractors are pluggable components that mine specific metadata
        (Labels, Selectors, Ports) required for cross-resource analysis
        in the later Suggester Stage.
        """
        path_keys = [pk for (_, pk) in self._path_stack]
        for extractor in get_extractors():
            try:
                extractor.extract_if_applicable(shard, key, val, path_keys, self._current_identity)
            except (AttributeError, KeyError, ImportError) as e:
                # Forensic catch for plugin instability.
                logger.debug(f"Extractor ({type(extractor).__name__}) failure: {e}")

    def _clean_id(self, val: Any) -> str:
        """DNA Sanitizer: Purges raw YAML tokens for accurate identity matching."""
        if val is None:
            return ""
        return str(val).strip().strip("'").strip('"')
