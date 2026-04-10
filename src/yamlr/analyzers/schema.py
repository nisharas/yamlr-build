"""
Yamlr Schema Analyzer Adapter
------------------------------
Standard adapter for the consolidated SchemaValidator.

Why: Bridges the diagnostic core with the Analyzer Registry system.
     Bypasses local re-definitions to eliminate code duplication.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
from yamlr.core.validation.schema import SchemaValidator

__all__ = ["SchemaAnalyzer"]


class SchemaAnalyzer(BaseAnalyzer):
    """
    Adapter for SchemaValidator into the Analyzer Registry.

    Why: Keeps the analyzer interface consistent while leveraging
         the hardened core validation layer.
    """

    def __init__(self, catalog: Optional[Dict[str, Any]] = None):
        """Initializes the analyzer with a shared or default catalog."""
        self.validator = SchemaValidator(catalog=catalog)

    @property
    def name(self) -> str:
        """Unique identifier for the schema analyzer."""
        return "schema"

    @property
    def analyzer_type(self) -> str:
        """Categorized as a content-based analyzer."""
        return "content"

    def analyze(self, resources: Any, **kwargs) -> List[AnalysisResult]:
        """
        Validates all provided resources against Kubernetes schemas.

        Why: Ensures 100% null-safety by delegating to the hardened core.
        """
        file_path = kwargs.get("file_path", "unknown")

        # [v0.1.0-HF] Support both single-doc and multi-doc manifests
        if isinstance(resources, dict):
            resources = [resources]
        elif not isinstance(resources, list):
            return []

        results: List[AnalysisResult] = []
        for doc in resources:
            if isinstance(doc, dict):
                results.extend(self.validator.validate_full_document(doc, file_path=file_path))
        return results
