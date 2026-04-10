"""
Yamlr COMPLIANCE ANALYZERS
---------------------------
Implements strict organizational and security compliance policies.
"""

from __future__ import annotations

from typing import Any, Dict, List

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer

__all__ = ["NamespaceEnforcementAnalyzer"]


class NamespaceEnforcementAnalyzer(BaseAnalyzer):
    """
    Enforces that all namespaced resources have an explicit namespace defined.

    Why: Deploying to 'default' by accident is a common cause of production outages
    and security leaks. This analyzer ensures intent is explicit.
    """

    # Cluster-scoped resources that do NOT need a namespace
    CLUSTER_SCOPED = {
        "Namespace",
        "Node",
        "ClusterRole",
        "ClusterRoleBinding",
        "PersistentVolume",
        "StorageClass",
        "CustomResourceDefinition",
        "PriorityClass",
        "RuntimeClass",
        "VolumeAttachment",
    }

    def __init__(self, default_namespace: str = "default"):
        super().__init__()
        self.default_namespace = default_namespace

    @property
    def name(self) -> str:
        return "namespace-enforcement"

    @property
    def analyzer_type(self) -> str:
        return "content"

    def analyze(self, resources: Any, **kwargs) -> List[AnalysisResult]:
        """Scans for missing namespaces in namespaced resources."""
        if not isinstance(resources, list):
            return []

        results: List[AnalysisResult] = []

        for resource in resources:
            kind = resource.get("kind")
            if not kind or kind in self.CLUSTER_SCOPED:
                continue

            metadata = resource.get("metadata", {})
            namespace = metadata.get("namespace")
            r_name = metadata.get("name", "unknown")

            if not namespace:
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id="rule/missing-namespace",
                        severity="warning",
                        message=f"{kind} '{r_name}' is missing an explicit namespace.",
                        rationale="Explicit namespaces prevent accidental deployment to the 'default' namespace, which is often unmanaged and lacks appropriate resource quotas or network policies.",
                        impact_description="The resource will be created in the active context's namespace (usually 'default'), potentially leading to resource collisions or security policy bypasses.",
                        risk_level="MEDIUM",
                        resource_name=r_name,
                        resource_kind=kind,
                        file_path="unknown",
                        line_no=0,
                    )
                )

        return results
