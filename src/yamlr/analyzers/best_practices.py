"""
Yamlr CORE ANALYZERS (Best Practices)
----------------------------------------
Standard Kubernetes policy checks implemented as Yamlr Analyzers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
from yamlr.analyzers.rules import Rules
from yamlr.core.context import HealContext
from yamlr.core.k8s_utils import extract_containers

logger = logging.getLogger("yamlr.analyzers.best_practices")

__all__ = ['ResourceAnalyzer', 'ImageAnalyzer', 'ServiceAnalyzer', 'ProbeAnalyzer', 'NetworkPolicyAnalyzer', 'ApiDeprecationAnalyzer']


class ResourceAnalyzer(BaseAnalyzer):
    """Enforces CPU/Memory requests and limits."""

    @property
    def name(self) -> str:
        """Returns the stable name of the resource analyzer.
        """
        return "resource-limit-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], context: Optional[HealContext] = None, **kwargs
    ) -> List[AnalysisResult]:
        """Analyzes CPU and Memory specifications.
        
        Why: To prevent resource starvation and OOM kills in production clusters.
        """
        results: List[AnalysisResult] = []
        # [OPTIMIZATION] Use cached container context if available
        containers = context.container_context if context else []
        logger.debug(f"ResourceAnalyzer: Found {len(containers)} containers in context")
        if not containers and resources:
            for resource in resources:
                containers.extend(extract_containers(resource))

        for container in containers:
            res_cfg = container.get("resources", {})
            
            # Check Requests
            if not res_cfg.get("requests"):
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id="resource-requests",
                        severity="WARNING",
                        message="Container is missing CPU/Memory requests.",
                        resource_name="unknown",
                        resource_kind="unknown",
                        file_path="unknown",
                    )
                )

            # Check Limits
            if not res_cfg.get("limits"):
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id="resource-limits",
                        severity="WARNING",
                        message="Container is missing CPU/Memory limits.",
                        resource_name="unknown",
                        resource_kind="unknown",
                        file_path="unknown",
                    )
                )
        return results


class ImageAnalyzer(BaseAnalyzer):
    """Enforces image tagging best practices."""

    @property
    def name(self) -> str:
        """Returns the stable name of the image analyzer.
        """
        return "image-tag-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], context: Optional[HealContext] = None, **kwargs
    ) -> List[AnalysisResult]:
        """Validates that images are pinned to a specific tag (not 'latest').
        
        Why: To ensure deployment predictability and avoid rolling out untested images.
        """
        results: List[AnalysisResult] = []
        # [OPTIMIZATION] Use cached container context if available
        containers = context.container_context if context else []
        logger.debug(f"ImageAnalyzer: Found {len(containers)} containers in context")
        if not containers and resources:
            for resource in resources:
                containers.extend(extract_containers(resource))

        for container in containers:
            image = container.get("image", "")
            if not image:
                continue

            if ":" not in image or image.endswith(":latest"):
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id="image-tag-check",
                        severity="ERROR",
                        message="Container image is missing a specific tag or uses 'latest'.",
                        resource_name="unknown",
                        resource_kind="unknown",
                        file_path="unknown",
                    )
                )
        return results


class ServiceAnalyzer(BaseAnalyzer):
    """Checks basic Service wiring best practices."""

    @property
    def name(self) -> str:
        """Returns the stable name of the service analyzer.
        """
        return "service-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], **kwargs
    ) -> List[AnalysisResult]:
        """Checks for missing selectors in Service manifests.
        
        Why: To prevent orphans where traffic enters a Service but has no Pods to route to.
        """
        results: List[AnalysisResult] = []
        for resource in resources:
            if resource.get("kind") != "Service":
                continue

            spec = resource.get("spec", {}) or {}
            svc_type = spec.get("type", "ClusterIP")
            selector = spec.get("selector")

            # Some headless or ExternalName Services legitimately skip selectors, so be lenient
            if svc_type in ("ExternalName",) or spec.get("clusterIP") == "None":
                continue

            if not selector:
                r_name = resource.get("metadata", {}).get("name", "unknown")
                r_kind = resource.get("kind", "Service")
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id="rule/service-no-selector",
                        severity="warning",
                        message="Service has no selector and is not an ExternalName or headless Service.",
                        rationale="A Service without a selector will not automatically route traffic to any Pods unless Endpoints are manually managed. This often indicates a misconfiguration.",
                        impact_description="Incoming traffic to this Service will result in No-Endpoint errors (e.g., 503 Service Unavailable), effectively orphaning the Service.",
                        risk_level="HIGH",
                        resource_name=r_name,
                        resource_kind=r_kind,
                        file_path="unknown",
                        line_number=0,
                    )
                )
        return results


class ProbeAnalyzer(BaseAnalyzer):
    """Ensures availability checks are defined."""

    @property
    def name(self) -> str:
        """Returns the stable name of the probe analyzer.
        """
        return "probe-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], context: Optional[HealContext] = None, **kwargs
    ) -> List[AnalysisResult]:
        """Ensures Containers have configured liveness and readiness probes.
        
        Why: To enable Kubernetes to automatically manage Container lifecycles and traffic readiness.
        """
        results: List[AnalysisResult] = []
        # [OPTIMIZATION] Use cached container context if available
        containers = context.container_context if context else []
        logger.debug(f"ProbeAnalyzer: Found {len(containers)} containers in context")
        if not containers and resources:
            for resource in resources:
                containers.extend(extract_containers(resource))

        for container in containers:
            if "livenessProbe" not in container:
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id=Rules.MISSING_LIVENESS,
                        severity="WARNING",
                        message="Container is missing a livenessProbe.",
                        resource_name="unknown",
                        resource_kind="unknown",
                        file_path="unknown",
                    )
                )

            if "readinessProbe" not in container:
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id=Rules.MISSING_READINESS,
                        severity="WARNING",
                        message="Container is missing a readinessProbe.",
                        resource_name="unknown",
                        resource_kind="unknown",
                        file_path="unknown",
                    )
                )
        return results

class NetworkPolicyAnalyzer(BaseAnalyzer):
    """Checks for default-deny NetworkPolicies in the workspace."""

    @property
    def name(self) -> str:
        """Returns the stable name of the network policy analyzer.
        """
        return "network-policy-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], **kwargs
    ) -> List[AnalysisResult]:
        """Detects workloads operating without a NetworkPolicy boundary.
        
        Why: To enforce the 'Zero Trust' principle within the cluster networking mesh.
        """
        results: List[AnalysisResult] = []
        has_netpol = any(r.get("kind") == "NetworkPolicy" for r in resources)
        
        if not has_netpol:
            for resource in resources:
                kind = resource.get("kind")
                if kind in ["Deployment", "StatefulSet", "DaemonSet", "Pod"]:
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id=Rules.NETWORK_POLICY_MISSING,
                            severity="WARNING",
                            message="No NetworkPolicy found for workloads in this directory.",
                            resource_name=resource.get("metadata", {}).get("name", "unknown"),
                            resource_kind=kind,
                            file_path="unknown",
                        )
                    )
                    break
        return results

class ApiDeprecationAnalyzer(BaseAnalyzer):
    """Surfaces SDK deprecation tracker info into visible CLI pipeline warnings."""

    @property
    def name(self) -> str:
        """Returns the stable name of the API deprecation analyzer.
        """
        return "api-deprecation-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a metadata-level analyzer.
        """
        return "metadata"

    def analyze(self, identities: List[Any], **kwargs) -> List[AnalysisResult]:
        """Identifies deprecated or removed API versions based on target cluster version.
        
        Why: To prevent deployment failures during Kubernetes upgrades.
        """
        results: List[AnalysisResult] = []
        for identity in identities:
            dep_info = getattr(identity, "deprecation_info", None)
            if dep_info:
                is_dict = isinstance(dep_info, dict)
                dep_api = dep_info.get("deprecated_api") if is_dict else dep_info.deprecated_api
                repl_api = dep_info.get("replacement_api") if is_dict else dep_info.replacement_api
                removed = dep_info.get("removed_in_version") if is_dict else dep_info.removed_in_version
                
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id="rule/api-deprecation",
                        severity="WARNING",
                        message=f"API '{dep_api}' is deprecated and removed in K8s v{removed}. Use '{repl_api}'.",
                        resource_name=getattr(identity, "name", "unknown") or "unknown",
                        resource_kind=getattr(identity, "kind", "Unknown") or "Unknown",
                        file_path="unknown",
                        line_number=getattr(identity, "line_number", 0)
                    )
                )
        return results
