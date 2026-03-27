from __future__ import annotations

from typing import Any, Dict, List

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer

__all__ = ['SecurityAnalyzer']


class SecurityAnalyzer(BaseAnalyzer):
    """Enforces Pod Security Standards (Baseline/Restricted)."""

    @property
    def name(self) -> str:
        """Returns the unique identifier for the security analyzer.
        """
        return "security-check"

    @property
    def analyzer_type(self) -> str:
        """Returns the type of analysis performed (content validation).
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], **kwargs
    ) -> List[AnalysisResult]:
        """Analyzes resources for security baseline compliance.
        
        Why: Integrates the centralized hardening engine into the scan pipeline.
        """
        from yamlr.core.engine.security import HardeningEngine
        
        results: List[AnalysisResult] = []
        engine = HardeningEngine(kwargs.get("allowed_host_paths"))
        
        for resource in resources:
            findings = engine.scan_manifest(resource)
            if not findings:
                continue

            r_name = resource.get("metadata", {}).get("name", "unknown")
            r_kind = resource.get("kind", "unknown")

            for f in findings:
                rule_id = f["rule_id"]
                
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id=rule_id,
                        severity=f["severity"],
                        message=f["message"],
                        risk_level=f["risk_level"],
                        resource_name=r_name,
                        resource_kind=r_kind,
                        file_path="unknown",
                        line_number=0,
                        # Rationale, impact, and external_url auto-fetched by AnalysisResult
                    )
                )

        return results
