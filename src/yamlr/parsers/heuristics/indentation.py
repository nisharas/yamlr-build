from __future__ import annotations
from typing import Any, Dict

from .base import BaseHeuristic
__all__ = ['TabExpansionHeuristic', 'SnapToGridHeuristic']


class TabExpansionHeuristic(BaseHeuristic):
    """
    Expands tabs to 2 spaces.
    
    Why: YAML parsers (including ruamel.yaml) often fail on literal tab 
         characters. Standardizing to spaces ensures cross-platform 
         structural stability.
    """
    @property
    def name(self) -> str:
        """Internal name for heuristic registry.
        
        Why: Programmatic identification during multi-stage parsing.
        """
        return "tab_expansion"

    @property
    def description(self) -> str:
        """Human-readable description.
        
        Why: CLI/UI feedback for active preprocessing stages.
        """
        return "Expands tabs to 2 spaces"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """Expands tab characters into spaces on a single line of YAML.
        
        Why: To ensure structural stability for parsers that are sensitive to literal tabs.
        """
        return line.replace("\t", "  ")


class SnapToGridHeuristic(BaseHeuristic):
    """
    Enforces even indentation (2-space standard).
    
    Why: Kubernetes manifests follow a strict 2-space indentation standard. 
    Developer environments with 4-space tabs or messy manual indentation 
    break the parser. This heuristic snaps odd-numbered indents to the 
    nearest grid point to ensure structural validity.
    """
    @property
    def name(self) -> str:
        """Internal name for heuristic registry.
        
        Why: Programmatic identification during multi-stage parsing.
        """
        return "snap_to_grid"

    @property
    def description(self) -> str:
        """Human-readable description.
        
        Why: CLI/UI feedback for active preprocessing stages.
        """
        return "Enforces even indentation (2-space standard)"

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """Enforces a 2-space grid for the line's indentation.
        
        Why: To satisfy the Kubernetes manifest standard and prevent structural ambiguity.
        """
        raw_line = line.rstrip()
        content = raw_line.lstrip()
        indent = len(raw_line) - len(content)

        if not content:
            return line

        if indent > 0 and indent % 2 != 0:
            if indent == 1:
                new_indent = 2
            else:
                new_indent = indent - 1

            if "stats" in context:
                context["stats"]["spacing_fixes"] += 1

            return (" " * new_indent) + content

        return line
