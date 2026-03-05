"""
Yamlr Enterprise: Kyverno Remediation Adapter
---------------------------------------------
Integrates Kyverno PolicyReports into the Yamlr cross-resource healing pipeline.
Parses native Kyverno JSON outputs and translates 'fail' results into
Yamlr AnalysisResult objects for automated mutation and reporting.

Author: Nishar A Sunkesala / Yamlr Team
"""

import json
import logging
from typing import Any, Dict, List, Optional
import os

try:
    from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
except ImportError:
    # Fallback for when running in isolation/tests
    from dataclasses import dataclass

    @dataclass
    class AnalysisResult:
        analyzer_name: str
        severity: str
        message: str
        resource_name: str
        resource_kind: str
        file_path: str
        rule_id: Optional[str] = None
        line_number: Optional[int] = None
        suggestion: Optional[str] = None
        fix_available: bool = False
        fix_id: Optional[str] = None

    class BaseAnalyzer:
        pass


logger = logging.getLogger("yamlr.pro.kyverno")


class KyvernoAdapter(BaseAnalyzer):
    """
    Ingests Kyverno PolicyReport / ClusterPolicyReport JSON
    and maps findings to Yamlr's auto-fix engine.
    """

    def __init__(self, report_path: str):
        self.report_path = report_path
        self._report_data = None

    @property
    def name(self) -> str:
        return "kyverno-adapter"

    @property
    def analyzer_type(self) -> str:
        # Runs at cross-resource phase as it depends on external ingestion
        return "metadata"

    def analyze(self, identities: List[Any]) -> List[AnalysisResult]:
        """
        Parses the Kyverno report and yields Yamlr AnalysisResults.
        """
        if not self.report_path or not os.path.exists(self.report_path):
            logger.warning(f"Kyverno PolicyReport not found: {self.report_path}")
            return []

        try:
            with open(self.report_path, "r", encoding="utf-8") as f:
                self._report_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load Kyverno report: {e}")
            return []

        return self._parse_report(self._report_data, identities)

    def _parse_report(
        self, data: Dict[str, Any], identities: List[Any]
    ) -> List[AnalysisResult]:
        results = []

        # Handle List of reports or single report
        reports = data.get("items", []) if "items" in data else [data]

        for report in reports:
            kind = report.get("kind")
            if kind not in ["PolicyReport", "ClusterPolicyReport"]:
                continue

            results_list = report.get("results", [])
            for res in results_list:
                if res.get("result") != "fail":
                    continue

                # Kyverno links multiple resources to one violation sometimes
                resources = res.get("resources", [])
                policy = res.get("policy", "kyverno-policy")
                rule = res.get("rule", "kyverno-rule")
                message = res.get("message", "Kyverno policy violation")

                # Map severity based on policy annotations or default to Error
                severity = res.get("severity", "error").lower()
                if severity not in ["info", "warning", "error", "high", "low", "medium"]:
                    severity = "error" if "require" in policy else "warning"

                for r in resources:
                    r_kind = r.get("kind", "Unknown")
                    r_name = r.get("name", "Unknown")
                    r_ns = r.get("namespace", "default")

                    # Try to map to an existing identity's file_path
                    fpath = "unknown"
                    for item in identities:
                        doc = item.to_dict() if hasattr(item, "to_dict") else item
                        item_kind = doc.get("kind", "Unknown")
                        item_name = doc.get("metadata", {}).get("name", "Unnamed")
                        item_ns = doc.get("metadata", {}).get("namespace", "default")

                        if r_kind == item_kind and r_name == item_name and (r_ns == item_ns or not r_ns):
                            fpath = getattr(item, "file_path", "unknown") if hasattr(item, "file_path") else "unknown"
                            break

                    results.append(
                        AnalysisResult(
                            analyzer_name="Kyverno Engine",
                            severity=severity,
                            message=f"[Kyverno] {message}",
                            rationale=f"Violated Kyverno Admission Policy '{policy}' (Rule: {rule})",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path=fpath,
                            rule_id=f"kyverno/{policy}/{rule}",
                            suggestion="Check Kyverno ClusterPolicy documentation for remediation steps.",
                        )
                    )

        return results
