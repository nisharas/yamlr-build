from __future__ import annotations
import logging
import re
from typing import Any, Dict, Set

from .base import BaseHeuristic

logger = logging.getLogger("yamlr.lexer.heuristics")
__all__ = ['MagicColonHeuristic', 'QuoteBalancingHeuristic', 'SpacingHeuristic']


class MagicColonHeuristic(BaseHeuristic):
    """
    Injects missing colons in 'key value' patterns (e.g., 'image nginx' -> 'image: nginx').
    
    Why: High-speed developer typing often omits colons. This heuristic recovers 
    intent by identifying known K8s keywords followed by whitespace and a value.
    
    Stopword Filtering: Essential to prevent false-positives in English comments 
    or descriptions (e.g., 'This is a test' shouldn't become 'This: is a test').
    """

    COMMON_ENGLISH_STOPWORDS: Set[str] = {
        "This", "The", "A", "An", "It", "If", "When", "Then", "For", "To", "Note", "But", "And", "Or",
    }

    @property
    def name(self) -> str:
        """Returns the internal name of the magic colon heuristic.
        
        Why: To uniquely identify the heuristic in logs and performance traces.
        """
        return "magic_colon"

    @property
    def description(self) -> str:
        """Returns a human-readable description of the magic colon heuristic.
        
        Why: To explain the heuristic's purpose in diagnostic outputs and reports.
        """
        return "Injects missing colons (key value -> key: value)"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """Applies magic colon injection to a line of YAML code.
        
        Why: To recover developer intent when colons are accidentally omitted during rapid editing.
        """
        if context.get("skip_punctuation_healing"):
            return line

        indent_len = len(line) - len(line.lstrip())
        indent_str = line[:indent_len]
        code_part = line.lstrip()

        if not code_part or code_part.startswith("#"):
            return line

        # Regex to find "(dash?) key space value"
        match = re.match(r"^(-\s+)?([a-zA-Z0-9_\-\.]+)\s+(.+)$", code_part)

        if match:
            dash_prefix = match.group(1) or ""
            key = match.group(2)
            val = match.group(3)

            if (
                key != "-"
                and not key.startswith("_")
                and key not in self.COMMON_ENGLISH_STOPWORDS
                and not (len(key) <= 2 and key.isupper())
            ):
                new_line = f"{indent_str}{dash_prefix}{key}: {val}"

                if "stats" in context:
                    context["stats"]["spacing_fixes"] += 1

                logger.debug(f"MagicColon: '{code_part}' -> '{key}: {val}'")
                return new_line

        return line


class QuoteBalancingHeuristic(BaseHeuristic):
    """Automatically closes unclosed quotes at the end of YAML values.
    
    Why: To prevent lexing failures when a developer forgets to type the closing quote.
    """
    @property
    def name(self) -> str:
        """Returns the internal name of the quote balancing heuristic.
        
        Why: To uniquely identify the heuristic in logs and performance traces.
        """
        return "quote_balancing"

    @property
    def description(self) -> str:
        """Returns a human-readable description of the quote balancing heuristic.
        
        Why: To explain the heuristic's purpose in diagnostic outputs and reports.
        """
        return "Closes unclosed quotes"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """Balances quotes on a single line of YAML code.
        
        Why: To ensure that string values are correctly terminated before they are sharded.
        """
        if context.get("skip_punctuation_healing"):
            return line

        if ":" not in line:
            return line

        _, _, v = line.partition(":")
        v_stripped = v.strip()

        if not v_stripped:
            return line

        if len(v_stripped) >= 1:
            first = v_stripped[0]
            if first in ('"', "'"):
                quote_count = v_stripped.count(first)
                if quote_count == 1 or (quote_count % 2 != 0 and not v_stripped.endswith(first)):
                    new_line = line.rstrip() + first
                    if "stats" in context:
                        context["stats"]["quote_repairs"] += 1
                    logger.debug(f"QuoteBalancing: Balanced unclosed {first} in line: {line.strip()}")
                    return new_line

        return line


class SpacingHeuristic(BaseHeuristic):
    """Injects mandatory spaces after YAML structural markers ('-' and ':').
    
    Why: YAML requires a space after certain markers; omitting them is a common syntax error.
    """
    @property
    def name(self) -> str:
        """Returns the internal name of the spacing heuristic.
        
        Why: To uniquely identify the heuristic in logs and performance traces.
        """
        return "spacing_fix"

    @property
    def description(self) -> str:
        """Returns a human-readable description of the spacing heuristic.
        
        Why: To explain the heuristic's purpose in diagnostic outputs and reports.
        """
        return "Fixes '-item' and 'key:value' spacing"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """Standardizes spacing around markers on a single line of YAML code.
        
        Why: To ensure the lexer can correctly identify structural boundaries.
        """
        if context.get("skip_punctuation_healing"):
            return line

        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        indent_str = line[:indent]

        # 1. Dash spacing "-item" -> "- item"
        if stripped.startswith("-") and not stripped.startswith("---") and len(stripped) > 1 and not stripped[1].isspace():
            new_content = "- " + stripped[1:]
            if "stats" in context:
                context["stats"]["spacing_fixes"] += 1
            return indent_str + new_content

        # 2. Colon spacing "key:value" -> "key: value"
        if ":" in stripped:
            k, _, v = stripped.partition(":")
            if v and not v.startswith(" ") and v.strip():
                new_content = f"{k}: {v}"
                if "stats" in context:
                    context["stats"]["spacing_fixes"] += 1
                return indent_str + new_content

        return line
