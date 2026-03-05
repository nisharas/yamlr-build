#!/usr/bin/env python3
"""
Registry Enforcement Analyzer
-----------------------------
Enforces that all container images match a list of trusted registries.
Derived from Yamlr Codebase Audit (Feb 2026).
"""

import logging
from typing import Any, Dict, List, Optional

from yamlr.analyzers.base import BaseAnalyzer, AnalysisResult
from yamlr.analyzers.rules import Rules

logger = logging.getLogger("yamlr.analyzers.registry_enforcement")

class RegistryAnalyzer(BaseAnalyzer):
    """
    Analyzes container images against a whitelist of trusted registries.
    """

    @property
    def name(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "registry-enforcement"

    @property
    def analyzer_type(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "content"

    def analyze(self, docs: List[Dict[str, Any]], **kwargs) -> List[AnalysisResult]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        trusted = kwargs.get("trusted_registries") or []
        if not trusted:
            return []

        results: List[AnalysisResult] = []
        for doc in docs:
            kind = doc.get("kind", "")
            if kind not in ["Deployment", "StatefulSet", "DaemonSet", "Pod", "Job", "CronJob"]:
                continue

            r_name = doc.get("metadata", {}).get("name", "unknown")
            r_kind = doc.get("kind", "unknown")

            pod_spec = self._get_pod_spec(doc)
            if not pod_spec:
                continue

            containers = pod_spec.get("containers", []) or []
            init_containers = pod_spec.get("initContainers", []) or []

            for container in containers + init_containers:
                image = container.get("image", "")
                if not image:
                    continue

                if not self._is_trusted(image, trusted):
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id=Rules.UNTRUSTED_REGISTRY,
                            severity="error",
                            message=f"Container '{container.get('name')}' uses untrusted image registry: {image}",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path="unknown",
                            line_number=0,
                        )
                    )
        return results

    def _is_trusted(self, image: str, trusted_list: List[str]) -> bool:
        """Checks if image matches any of the trusted registry prefixes."""
        # Simple prefix match for now (e.g., 'gcr.io/my-project' matches 'gcr.io/my-project/nginx')
        for prefix in trusted_list:
            if image.startswith(prefix):
                return True
        return False

    def _get_pod_spec(self, resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extracts pod spec from various resource types."""
        kind = resource.get("kind")
        if kind == "Pod":
            return resource.get("spec")
        elif kind in ["Deployment", "StatefulSet", "DaemonSet", "Job"]:
            template = resource.get("spec", {}).get("template", {})
            return template.get("spec")
        elif kind == "CronJob":
            template = resource.get("spec", {}).get("jobTemplate", {}).get("spec", {}).get("template", {})
            return template.get("spec")
        return None
