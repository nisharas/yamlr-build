from __future__ import annotations

import logging
from typing import Any, Dict

from .base import BaseHeuristic

logger = logging.getLogger("yamlr.lexer.heuristics")
__all__ = ["BooleanGuardHeuristic"]


class BooleanGuardHeuristic(BaseHeuristic):
    """
    Protects YAML 1.1 booleans (yes, no, on, off) from being parsed as actual booleans.

    Why: Legacy clusters often use 'yes/no' in environment variables or ConfigMaps.
    YAML 1.1 (used by many older tools) parses these as booleans. Yamlr forces
    them to strings to ensure semantic DNA integrity.
    """

    BOOLEAN_STRINGS = {"yes", "no", "y", "n", "on", "off"}

    @property
    def name(self) -> str:
        return "boolean_guard"

    @property
    def description(self) -> str:
        return "Protects YAML 1.1 boolean-lookalikes by quoting them"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """
        Detects unquoted boolean-lookalikes in values and quotes them.
        """
        if ":" not in line or context.get("in_block", False):
            return line

        # Split into key and value parts
        # We use a simple partition because we are at the raw line level here
        key_part, sep, val_part = line.partition(":")

        stripped_val = val_part.strip()
        if not stripped_val:
            return line

        # Check if the value is one of the "Norway Problem" booleans
        # and is not already quoted.
        if stripped_val.lower() in self.BOOLEAN_STRINGS:
            # Reconstruct the line with quoted value
            indent_and_key = key_part
            # Preserving the exact spacing after colon if possible
            colon_space = val_part[: val_part.find(stripped_val)]

            new_line = f'{indent_and_key}:{colon_space}"{stripped_val}"'.rstrip()

            if "stats" in context:
                context["stats"]["quote_repairs"] = context["stats"].get("quote_repairs", 0) + 1

            logger.debug(f"BooleanGuard: Quoted '{stripped_val}' in line: {line.strip()}")
            return new_line

        return line
