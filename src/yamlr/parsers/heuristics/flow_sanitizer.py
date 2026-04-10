from __future__ import annotations

import logging
import re
from typing import Any, Dict

from .base import BaseHeuristic

logger = logging.getLogger("yamlr.lexer.heuristics")
__all__ = ["FlowStyleHeuristic"]


class FlowStyleHeuristic(BaseHeuristic):
    """
    Surgically removes trailing commas in flow-style collections.

    Why: Flow style like [a, b, ] is technically valid in some YAML versions
    but causes "trailing comma" errors in many strict parsers (e.g., standard Python yaml).
    Yamlr cleans these up to maximize interoperability.
    """

    @property
    def name(self) -> str:
        return "flow_style_sanitizer"

    @property
    def description(self) -> str:
        return "Removes trailing commas in flow-style lists and maps"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """
        Cleans up flow-style trailing commas.
        Example: [item1, item2, ] -> [item1, item2]
        """
        if context.get("in_block", False):
            return line

        # Very focused regex for trailing commas before closing brackets
        # Works on both [] and {}
        # Pattern: comma + optional space + closing bracket
        # Group 1: The part before the comma
        # Group 2: The closing bracket

        repaired = line

        # Iteratively fix for cases with multiple nested flows on one line
        # but usually one skip is enough for typical K8s manifests
        repaired = re.sub(r",\s*(\])", r"\1", repaired)
        repaired = re.sub(r",\s*(\})", r"\1", repaired)

        if repaired != line:
            if "stats" in context:
                context["stats"]["spacing_fixes"] = context["stats"].get("spacing_fixes", 0) + 1
            logger.debug(f"FlowStyle: Removed trailing comma in line: {line.strip()}")

        return repaired
