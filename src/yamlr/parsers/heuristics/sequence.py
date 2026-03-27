from __future__ import annotations
from typing import Any, Dict

from .base import BaseHeuristic
__all__ = ['FragmentedSequenceHeuristic']


class FragmentedSequenceHeuristic(BaseHeuristic):
    """
    Heals broken or fragmented YAML sequence indicators.
    
    Why: LEGACY AUDIT V3. Bad copy-pastes often result in '- - item' 
         or '-- item'. Many users also omit the space in '-item'. 
         Yamlr normalizes these to '- item' for structural clarity.
    """

    @property
    def name(self) -> str:
        return "fragmented_sequence"

    @property
    def description(self) -> str:
        return "Normalizes broken sequence indicators (-- item, - - item, -item)"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """
        Detects and repairs fragmented or fused sequence bullets.
        """
        if context.get("in_block", False):
            return line

        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        indent_str = line[:indent]

        # 1. Double dash normalized: "- - item" -> "- item"
        if stripped.startswith("- -"):
            if "stats" in context:
                context["stats"]["double_dash_normalized"] = context["stats"].get("double_dash_normalized", 0) + 1
            return indent_str + "- " + stripped[3:].lstrip()

        # 2. Fragmented marker: "-- item" -> "- item" (common in legacy Helm)
        if stripped.startswith("--") and not stripped.startswith("---"):
            if "stats" in context:
                context["stats"]["double_dash_normalized"] = context["stats"].get("double_dash_normalized", 0) + 1
            return indent_str + "- " + stripped[2:].lstrip()

        # 3. Fused item: "-item" -> "- item"
        if stripped.startswith("-") and len(stripped) > 1 and stripped[1].isalpha():
            if "stats" in context:
                context["stats"]["spacing_fixes"] = context["stats"].get("spacing_fixes", 0) + 1
            return indent_str + "- " + stripped[1:]

        return line
