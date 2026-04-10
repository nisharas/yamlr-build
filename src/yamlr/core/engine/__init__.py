"""
Yamlr ENGINE PACKAGE
--------------------
Central execution engine for manifest processing.
"""

from __future__ import annotations

from yamlr.core.engine.base import YamlrEngine
from yamlr.core.engine.models import AnalysisResult

__all__ = ["YamlrEngine", "AnalysisResult"]
