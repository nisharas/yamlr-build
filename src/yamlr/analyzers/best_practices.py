"""
Yamlr CORE ANALYZERS (Best Practices)
----------------------------------------
Standard Kubernetes policy checks implemented as Yamlr Analyzers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
from yamlr.analyzers.rules import Rules
from yamlr.core.context import HealContext
from yamlr.core.k8s_utils import extract_containers

logger = logging.getLogger("yamlr.analyzers.best_practices")

__all__ = [
    "ResourceAnalyzer",
    "ImageAnalyzer",
    "ServiceAnalyzer",
    "ProbeAnalyzer",
    "NetworkPolicyAnalyzer",
    "ApiDeprecationAnalyzer",
    "ReliabilityAnalyzer",
]


class ResourceAnalyzer(BaseAnalyzer):
    """Enforces CPU/Memory requests and limits."""

    @property
    def name(self) -> str:
        """Returns the stable name of the resource analyzer."""
        return "resource-limit-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer."""
        return "content"

    def analyze(self, resources: Any, context: Optional[HealContext] = None, **kwargs) -> List[AnalysisResult]:
        """Analyzes CPU and Memory specifications."""
        if not isinstance(resources, list):
            return []

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
        """Returns the stable name of the image analyzer."""
        return "image-tag-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer."""
        return "content"

    def analyze(self, resources: Any, context: Optional[HealContext] = None, **kwargs) -> List[AnalysisResult]:
        """Validates that images are pinned to a specific tag (not 'latest')."""
        if not isinstance(resources, list):
            return []

        results: List[AnalysisResult] = []
        # [OPTIMIZATION] Use cached container context if available
        containers = context.container_context if context else []
        logger.debug(f"ImageAnalyzer: Found {len(containers)} containers in context")
        if not containers and resources:
            for resource in resources:
                kind = resource.get("kind") if hasattr(resource, "get") else "Unknown"
                name = resource.get("metadata", {}).get("name") if hasattr(resource, "get") else "Unknown"
                # [DEBUG-V3] Trace resource ingestion
                import sys
                print(f"DEBUG: ImageAnalyzer auditing {kind}/{name}", file=sys.stderr)
                
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
        """Returns the stable name of the service analyzer."""
        return "service-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer."""
        return "content"

    def analyze(self, resources: Any, **kwargs) -> List[AnalysisResult]:
        """Checks for missing selectors in Service manifests."""
        if not isinstance(resources, list):
            return []

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
        """Returns the stable name of the probe analyzer."""
        return "probe-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer."""
        return "content"

    def analyze(self, resources: Any, context: Optional[HealContext] = None, **kwargs) -> List[AnalysisResult]:
        """Ensures Containers have configured liveness and readiness probes."""
        if not isinstance(resources, list):
            return []

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

            # [GOOGLE-SCALE] StartupProbe Enforcement
            # Why: StartupProbes prevent slow-starting containers from being killed by liveness probes.
            if "startupProbe" not in container:
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id="reliability/missing-startup-probe",
                        severity="INFO",
                        message="Container is missing a startupProbe (Recommended for slow-start apps).",
                        resource_name="unknown",
                        resource_kind="unknown",
                        file_path="unknown",
                        suggestion="Add startupProbe to handle initial bootstrap latency.",
                    )
                )
        return results


class ReliabilityAnalyzer(BaseAnalyzer):
    """Enforces SRE-level reliability and termination grace periods."""

    @property
    def name(self) -> str:
        return "reliability-audit"

    @property
    def analyzer_type(self) -> str:
        return "content"

    def analyze(self, resources: Any, **kwargs) -> List[AnalysisResult]:
        """Audits manifests for SRE-critical reliability settings."""
        if not isinstance(resources, list):
            return []

        results = []
        for resource in resources:
            if resource.get("kind") not in ["Pod", "Deployment", "StatefulSet", "DaemonSet"]:
                continue

            spec = resource.get("spec", {})
            if resource.get("kind") != "Pod":
                spec = spec.get("template", {}).get("spec", {})

            # 1. Termination Grace Period
            # Why: GKE/EKS recommend >= 30s to allow proper connection draining.
            grace = spec.get("terminationGracePeriodSeconds", 30)
            if grace < 30:
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        severity="WARNING",
                        message=f"Termination Grace Period too low ({grace}s). Recommended: >= 30s.",
                        resource_name=resource.get("metadata", {}).get("name", "unknown"),
                        resource_kind=resource.get("kind", "pod"),
                        file_path="scan",
                        suggestion="Set terminationGracePeriodSeconds: 30",
                        rule_id="reliability/grace-period",
                    )
                )

            # 2. [SRE-01] Readiness Gates
            # Why: Essential for external LB readiness (GKE Ingress, AWS ALB/NLB).
            if not spec.get("readinessGates"):
                # Check if likely using an external service
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        severity="INFO",
                        message="Missing readinessGates. Recommended for workloads using external Cloud LBs.",
                        resource_name=resource.get("metadata", {}).get("name", "unknown"),
                        resource_kind=resource.get("kind", "pod"),
                        file_path="scan",
                        suggestion="Add readinessGates for cloud-provider integration.",
                        rule_id="reliability/missing-readiness-gates",
                    )
                )

            # 3. [SRE-02] Topology Spread Constraints
            # Why: Prevents single-point-of-failure by distributing Pods across zones/nodes.
            if not spec.get("topologySpreadConstraints"):
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        severity="WARNING",
                        message="Missing topologySpreadConstraints (HA Risk).",
                        resource_name=resource.get("metadata", {}).get("name", "unknown"),
                        resource_kind=resource.get("kind", "pod"),
                        file_path="scan",
                        suggestion="Implement topologySpreadConstraints for multi-zone distribution.",
                        rule_id="reliability/topology-spread-missing",
                    )
                )

            # 4. [SRE-03] Priority Class Name
            # Why: Ensures critical workloads are not evicted before lower-priority ones.
            if not spec.get("priorityClassName"):
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        severity="INFO",
                        message="Explicit priorityClassName is missing.",
                        resource_name=resource.get("metadata", {}).get("name", "unknown"),
                        resource_kind=resource.get("kind", "pod"),
                        file_path="scan",
                        suggestion="Set priorityClassName to prevent accidental eviction.",
                        rule_id="reliability/priority-class-missing",
                    )
                )
        return results


class NetworkPolicyAnalyzer(BaseAnalyzer):
    """Checks for default-deny NetworkPolicies in the workspace."""

    @property
    def name(self) -> str:
        """Returns the stable name of the network policy analyzer."""
        return "network-policy-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a content-level analyzer."""
        return "content"

    def analyze(self, resources: Any, **kwargs) -> List[AnalysisResult]:
        """Detects workloads operating without a NetworkPolicy boundary."""
        if not isinstance(resources, list):
            return []

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
        """Returns the stable name of the API deprecation analyzer."""
        return "api-deprecation-check"

    @property
    def analyzer_type(self) -> str:
        """Indicates this is a metadata-level analyzer."""
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
                        line_no=getattr(identity, "line_number", 0),
                    )
                )
        return results
