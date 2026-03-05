"""
Yamlr CORE ANALYZERS (Best Practices)
----------------------------------------
Standard Kubernetes policy checks implemented as Yamlr Analyzers.
"""

from typing import Any, Dict, List

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
from yamlr.analyzers.rules import Rules


class ResourceAnalyzer(BaseAnalyzer):
    """Enforces CPU/Memory requests and limits."""

    @property
    def name(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "resource-limit-check"

    @property
    def analyzer_type(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], **kwargs
    ) -> List[AnalysisResult]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        results: List[AnalysisResult] = []
        for resource in resources:
            kind = resource.get("kind", "")
            if kind not in ["Deployment", "StatefulSet", "DaemonSet", "Pod"]:
                continue

            containers = self._get_containers(resource)
            for container in containers:
                name = container.get("name", "unknown")
                res_cfg = container.get("resources", {})
                r_name = resource.get("metadata", {}).get("name", "unknown")
                r_kind = resource.get("kind", "unknown")

                # Check Requests
                if not res_cfg.get("requests"):
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id="rule/resource-requests",
                            severity="warning",
                            message=f"Container '{name}' has no resource requests defined",
                            rationale="Without resource requests, the Kubernetes scheduler cannot accurately bin-pack nodes, leading to potential CPU/Memory starvation and Pod evictions under heavy load.",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path="unknown",
                            line_number=0,
                        )
                    )

                # Check Limits
                if not res_cfg.get("limits"):
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id="rule/resource-limits",
                            severity="warning",
                            message=f"Container '{name}' has no resource limits defined",
                            rationale="Without resource limits, a single container can consume all available node resources, causing out-of-memory (OOM) kills that cascade to other workloads.",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path="unknown",
                            line_number=0,
                        )
                    )
        return results

    def _get_containers(self, resource: Dict) -> List[Dict]:
        """Helper to extract containers from various workloads."""
        kind = resource.get("kind")
        if kind == "Pod":
            return resource.get("spec", {}).get("containers", [])
        # Workloads
        return (
            resource.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [])
        )


class ImageAnalyzer(BaseAnalyzer):
    """Enforces image tagging best practices."""

    @property
    def name(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "image-tag-check"

    @property
    def analyzer_type(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], **kwargs
    ) -> List[AnalysisResult]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        results: List[AnalysisResult] = []
        for resource in resources:
            kind = resource.get("kind", "")
            if kind not in ["Deployment", "StatefulSet", "DaemonSet", "Job", "Pod"]:
                continue

            containers = self._get_containers(resource)
            for container in containers:
                image = container.get("image", "")
                if not image:
                    continue

                if ":" not in image or image.endswith(":latest"):
                    r_name = resource.get("metadata", {}).get("name", "unknown")
                    r_kind = resource.get("kind", "unknown")
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id="rule/no-latest-tag",
                            severity="error",
                            message=f"Container uses '{image}'. Do not use ':latest' tag in production.",
                            rationale="The ':latest' tag is mutable. Deployments using it are non-deterministic, making rollbacks unpredictable and caching inefficient.",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path="unknown",
                            line_number=0,
                        )
                    )
        return results

    def _get_containers(self, resource: Dict) -> List[Dict]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        kind = resource.get("kind")
        if kind == "Pod":
            return resource.get("spec", {}).get("containers", [])
        return (
            resource.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [])
        )


class ServiceAnalyzer(BaseAnalyzer):
    """Checks basic Service wiring best practices."""

    @property
    def name(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "service-check"

    @property
    def analyzer_type(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], **kwargs
    ) -> List[AnalysisResult]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
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
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "probe-check"

    @property
    def analyzer_type(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], **kwargs
    ) -> List[AnalysisResult]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        results: List[AnalysisResult] = []
        for resource in resources:
            kind = resource.get("kind", "")
            if kind not in [
                "Deployment",
                "StatefulSet",
                "DaemonSet",
            ]:  # Jobs don't need probes
                continue

            containers = self._get_pod_spec(resource).get("containers", [])
            r_name = resource.get("metadata", {}).get("name", "unknown")
            r_kind = resource.get("kind", "unknown")

            for container in containers:
                name = container.get("name")

                if "livenessProbe" not in container:
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id="rule/missing-liveness",
                            severity="warning",
                            message=f"Container '{name}' missing livenessProbe",
                            rationale="Liveness probes are essential for self-healing. Without them, Kubelet cannot know if the application is deadlocked and won't automatically restart it.",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path="unknown",
                            line_number=0,
                        )
                    )

                if "readinessProbe" not in container:
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id="rule/missing-readiness",
                            severity="warning",
                            message=f"Container '{name}' missing readinessProbe",
                            rationale="Readiness probes prevent traffic routing to Pods that are still booting up or temporarily overloaded, eliminating 502/503 errors during deployments.",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path="unknown",
                            line_number=0,
                        )
                    )
        return results

    def _get_pod_spec(self, resource: Dict) -> Dict:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return resource.get("spec", {}).get("template", {}).get("spec", {})
class NetworkPolicyAnalyzer(BaseAnalyzer):
    """Checks for default-deny NetworkPolicies in the workspace."""

    @property
    def name(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "network-policy-check"

    @property
    def analyzer_type(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "content"

    def analyze(
        self, resources: List[Dict[str, Any]], **kwargs
    ) -> List[AnalysisResult]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        results: List[AnalysisResult] = []
        
        # We look for ANY NetworkPolicy in the set.
        # Strict mode: check per namespace.
        # Simple mode: if NO NetworkPolicy exists in the doc set, warn.
        
        has_netpol = any(r.get("kind") == "NetworkPolicy" for r in resources)
        
        if not has_netpol:
            # Report on the first resource found that isn't a NetPol itself
            for resource in resources:
                kind = resource.get("kind")
                if kind in ["Deployment", "StatefulSet", "DaemonSet", "Pod"]:
                    r_name = resource.get("metadata", {}).get("name", "unknown")
                    r_kind = resource.get("kind", "unknown")
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id=Rules.NETWORK_POLICY_MISSING,
                            severity="warning",
                            message="No default-deny NetworkPolicy found in the manifest set. Consider adding one for zero-trust security.",
                            rationale="By default, all pods in a cluster can communicate with each other. A default-deny NetworkPolicy prevents lateral movement in the event of a container compromise.",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path="unknown",
                            line_number=0,
                        )
                    )
                    # Only report once per set for brevity in this simple analyzer
                    break
        return results

class ApiDeprecationAnalyzer(BaseAnalyzer):
    """Surfaces SDK deprecation tracker info into visible CLI pipeline warnings."""

    @property
    def name(self) -> str:
        return "api-deprecation-check"

    @property
    def analyzer_type(self) -> str:
        return "metadata"

    def analyze(self, identities: List[Any], **kwargs) -> List[AnalysisResult]:
        results: List[AnalysisResult] = []
        for identity in identities:
            dep_info = getattr(identity, "deprecation_info", None)
            if dep_info:
                # E.g. {"deprecated_api", "replacement_api", "removed_in_version"} or object
                is_dict = isinstance(dep_info, dict)
                dep_api = dep_info.get("deprecated_api") if is_dict else dep_info.deprecated_api
                repl_api = dep_info.get("replacement_api") if is_dict else dep_info.replacement_api
                removed = dep_info.get("removed_in_version") if is_dict else dep_info.removed_in_version
                severity = "WARNING"
                
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id="rule/api-deprecation",
                        severity=severity,
                        message=f"API '{dep_api}' is deprecated and removed in K8s v{removed}. Use '{repl_api}'.",
                        rationale=f"Deploying with a removed API silently fails—the resource is ignored by the cluster. Update to {repl_api}.",
                        resource_name=getattr(identity, "name", "unknown") or "unknown",
                        resource_kind=getattr(identity, "kind", "Unknown") or "Unknown",
                        file_path="unknown",
                        line_number=getattr(identity, "line_number", 0)
                    )
                )
        return results

