from __future__ import annotations
from typing import Any, Dict, Optional

from yamlr.models import K8S_CORE_KEYS
from .base import BaseHeuristic
__all__ = ['KeywordFusionHeuristic', 'MissingColonHeuristic']


class KeywordFusionHeuristic(BaseHeuristic):
    """
    Fixes fused K8s keywords like 'kindService' -> 'kind: Service'.
    """
    
    SAFE_KEYWORDS = K8S_CORE_KEYS

    @property
    def name(self) -> str:
        return "keyword_fusion"

    @property
    def description(self) -> str:
        return "Separates fused keywords (kindService -> kind: Service)"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        if context.get("in_block", False):
            return line

        stripped = line.strip()
        if not stripped or ":" in line or "[" in line or "{" in line:
            return line

        fused = self._find_fused_keyword(stripped)
        if fused:
            key, suffix = fused
            indent = len(line) - len(line.lstrip())
            if "stats" in context:
                context["stats"]["spacing_fixes"] = context["stats"].get("spacing_fixes", 0) + 1
            return (" " * indent) + f"{key}: {suffix}"
            
        return line

    def _find_fused_keyword(self, stripped: str) -> Optional[Tuple[str, str]]:
        """Identifies a known keyword fused to its value (e.g. kindService)."""
        for key in self.SAFE_KEYWORDS:
            if stripped.startswith(key) and len(stripped) > len(key):
                suffix = stripped[len(key):]
                # If suffix starts with uppercase, it's likely a ValueFusedToKey
                if suffix[0].isupper() or suffix[0].isdigit() or (key == "apiVersion" and suffix.lower().startswith("v")):
                    return key, suffix
        return None


class MissingColonHeuristic(BaseHeuristic):
    """
    Heals missing colons for parent map keys based on indentation lookahead.
    """

    @property
    def name(self) -> str:
        return "missing_colon_lookahead"

    @property
    def description(self) -> str:
        return "Injects missing colons for parent keys"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        if context.get("in_block", False):
            return line

        stripped = line.strip()
        if not stripped or ":" in stripped or "[" in stripped or "{" in stripped:
            return line

        # Requires lookahead info from Lexer (passed via context)
        next_line = context.get("next_line")
        if next_line:
            cur_indent = len(line) - len(line.lstrip())
            next_indent = len(next_line) - len(next_line.lstrip())
            
            if next_indent > cur_indent and next_line.strip():
                if "stats" in context:
                    context["stats"]["spacing_fixes"] = context["stats"].get("spacing_fixes", 0) + 1
                return line.rstrip() + ":"
        
        return line
