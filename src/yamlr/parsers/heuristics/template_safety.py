#!/usr/bin/env python3
"""
Yamlr TEMPLATE SAFETY HEURISTIC
---------------------------------
Protects Helm/Jinja2 template variables ({{ ... }}) from being mangled
by other lexical heuristics (e.g., MagicColon, QuoteBalancing).

Why: GitOps manifests often contain template logic that is technically
     invalid YAML but should be preserved by the "forgiving" parser.
"""

import re
from typing import Any, Dict
from .base import BaseHeuristic

class TemplateSafetyHeuristic(BaseHeuristic):
    """
    Identifies template variables and ensures they are treated as atomic units.
    """

    @property
    def name(self) -> str:
        return "template_safety"

    @property
    def description(self) -> str:
        return "Protects Helm/Jinja2 template variables"

    # Matches {{ ... }}, {% ... %}, and {# ... #}
    TEMPLATE_PATTERN = re.compile(r'(\{\{.*?\}\}|\{\%.*?\%\}|\{\#.*?\#\})')

    def apply(self, line: str, context: Dict[str, Any]) -> str:
        """
        If a line contains template markers, we tag the context
        to signal other heuristics to be conservative.
        """
        if self.TEMPLATE_PATTERN.search(line):
            # We don't necessarily modify the line here, but we set a flag
            # in the context that subsequent heuristics in the pipeline can check.
            context["has_templates"] = True
            
            # [Aggressive Forgiveness] 
            # If the line is JUST a template block, we should probably 
            # avoid ANY punctuation healing.
            stripped = line.strip()
            if stripped.startswith("{{") and stripped.endswith("}}"):
                context["skip_punctuation_healing"] = True
        else:
            context["has_templates"] = False
            context["skip_punctuation_healing"] = False

        return line
