from typing import Any, Dict, List

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
from yamlr.analyzers.rules import Rules

class SecurityAnalyzer(BaseAnalyzer):
    """Enforces Pod Security Standards (Baseline/Restricted)."""

    @property
    def name(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "security-check"

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

            r_name = resource.get("metadata", {}).get("name", "unknown")
            r_kind = resource.get("kind", "unknown")

            pod_spec = self._get_pod_spec(resource)
            if not pod_spec:
                continue

            host_network = pod_spec.get("hostNetwork", False)
            namespace = resource.get("metadata", {}).get("namespace", "default")

            if host_network and namespace not in ("kube-system", "kube-public"):
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id=Rules.HOST_NETWORK,
                        severity="warning",
                        message=f"Workload in namespace '{namespace}' uses hostNetwork, which is risky outside system namespaces.",
                        rationale="hostNetwork exposes the node's network namespace to the Pod, bypassing network isolation. A compromised Pod could sniff all traffic on the node.",
                        resource_name=r_name,
                        resource_kind=r_kind,
                        file_path="unknown",
                        line_number=0,
                    )
                )

            # Check RunAsNonRoot (Pod Level)
            security_ctx = pod_spec.get("securityContext", {})
            if not security_ctx.get("runAsNonRoot", False):
                results.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id="rule/run-as-non-root",
                        severity="error",
                        message="Pod securityContext should set 'runAsNonRoot: true'",
                        rationale="Running containers as root allows an attacker who escapes the container to gain full root privileges on the underlying host node.",
                        resource_name=r_name,
                        resource_kind=r_kind,
                        file_path="unknown",
                        line_number=0,
                    )
                )

            # Check Privileged (Container Level)
            for container in pod_spec.get("containers", []):
                ctx = container.get("securityContext", {})
                name = container.get("name", "unknown")
                if ctx.get("privileged", False):
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id="rule/no-privileged",
                            severity="error",
                            message=f"Container '{container.get('name')}' is running in Privileged mode.",
                            rationale="Privileged mode disables almost all container security isolations. It is equivalent to giving the container full root shell access to the host machine.",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path="unknown",
                            line_number=0,
                        )
                    )

                # allowPrivilegeEscalation
                ape = ctx.get("allowPrivilegeEscalation")
                if ape is True:
                    results.append(
                        AnalysisResult(
                            analyzer_name=self.name,
                            rule_id="rule/allow-privilege-escalation",
                            severity="high",
                            message=f"Container '{name}' sets allowPrivilegeEscalation: true.",
                            rationale="When set to true, processes inside the container can gain more privileges than their parent process, defeating security boundaries.",
                            resource_name=r_name,
                            resource_kind=r_kind,
                            file_path="unknown",
                            line_number=0,
                        )
                    )

            # hostPath check
            results.extend(
                self._check_unsafe_hostpaths(resource, pod_spec, r_name, r_kind, **kwargs)
            )

        return results

    def _get_pod_spec(self, resource: Dict) -> Dict:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        kind = resource.get("kind")
        if kind == "Pod":
            return resource.get("spec", {})
        return resource.get("spec", {}).get("template", {}).get("spec", {})

    def _check_unsafe_hostpaths(
        self,
        resource: Dict,
        pod_spec: Dict,
        r_name: str,
        r_kind: str,
        **kwargs
    ) -> List[AnalysisResult]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        results: List[AnalysisResult] = []
        volumes = pod_spec.get("volumes", []) or []

        # Use provided whitelist from kwargs, or fallback to defaults
        allowed_prefixes = kwargs.get("allowed_host_paths") or ["/var/log", "/tmp", "/var/tmp"]

        for vol in volumes:
            hp = vol.get("hostPath")
            if not isinstance(hp, dict):
                continue
            path = hp.get("path")
            if not path:
                continue
            if any(path.startswith(p) for p in allowed_prefixes):
                continue

            results.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    rule_id=Rules.UNSAFE_HOSTPATH,
                    severity="high",
                    message=f"Volume '{vol.get('name', 'unknown')}' uses unsafe hostPath '{path}'.",
                    rationale="Mounting sensitive host paths allows a container to read or write to the node's filesystem, potentially accessing secrets like the kubelet config or overwriting system files.",
                    resource_name=r_name,
                    resource_kind=r_kind,
                    file_path="unknown",
                    line_number=0,
                )
            )
        return results
