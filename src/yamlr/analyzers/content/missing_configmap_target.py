from __future__ import annotations

from typing import Any, Dict, List, Set

from yamlr.analyzers.base import AnalysisResult, BaseAnalyzer
from yamlr.analyzers.rules import Rules

__all__ = ["MissingConfigMapTargetAnalyzer"]


class MissingConfigMapTargetAnalyzer(BaseAnalyzer):
    """
    Detect references to ConfigMaps (envFrom/env/volumes) that
    are not defined in the current manifest set.
    """

    @property
    def name(self) -> str:
        """Returns the internal name of the missing ConfigMap target analyzer.

        Why: To uniquely identify the analyzer in reports and rule registries.
        """
        return "missing-configmap-target"

    @property
    def analyzer_type(self) -> str:
        """Returns the type category of the analyzer.

        Why: To group analyzers by their operational domain (e.g., content, structural).
        """
        return "content"

    def analyze(self, docs: Any, **kwargs) -> List[AnalysisResult]:
        """Performs cross-resource analysis to detect missing ConfigMap references."""
        if not isinstance(docs, list):
            return []

        results: List[AnalysisResult] = []
        defined_cm_names = self._collect_configmaps(docs)

        for doc in docs:
            if self._is_workload(doc):
                self._analyze_workload(doc, defined_cm_names, results)

        return results

    def _is_workload(self, doc: Dict[str, Any]) -> bool:
        """Determines if a document represents a Kubernetes workload."""
        kind = (doc.get("kind") or "").lower()
        return kind in {"deployment", "statefulset", "daemonset", "job", "cronjob", "replicaset"}

    def _analyze_workload(self, doc: Dict[str, Any], defined_cm_names: Set[str], results: List[AnalysisResult]):
        """Helper to analyze a single workload document."""
        spec = doc.get("spec") or {}
        template = spec.get("template") or {}
        if not isinstance(template, dict):
            return

        pod_spec = template.get("spec") or {}
        if not isinstance(pod_spec, dict):
            return

        containers = pod_spec.get("containers") or []
        if isinstance(containers, list):
            for c in containers:
                if isinstance(c, dict):
                    self._check_container_envfrom(c, defined_cm_names, doc, results)
                    self._check_container_env(c, defined_cm_names, doc, results)

        volumes = pod_spec.get("volumes") or []
        if isinstance(volumes, list):
            self._check_volumes(volumes, defined_cm_names, doc, results)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _collect_configmaps(self, docs: List[Dict[str, Any]]) -> Set[str]:
        """Scans the manifest set to index all defined ConfigMap names.

        Why: To provide a lookup table for validating whether a reference has a corresponding target.
        """
        names: Set[str] = set()
        for d in docs:
            if (d.get("kind") or "").lower() != "configmap":
                continue
            meta = d.get("metadata") or {}
            name = meta.get("name")
            if isinstance(name, str) and name:
                names.add(name)
        return names

    def _make_result(
        self,
        doc: Dict[str, Any],
        cm_name: str,
        field_path: str,
    ) -> AnalysisResult:
        """Factory method for creating structured results for missing ConfigMap findings.

        Why: To ensure consistent reporting and actionable feedback for the user.
        """
        meta = doc.get("metadata") or {}
        obj_name = meta.get("name", "<unknown>")

        message = f'ConfigMap "{cm_name}" is not defined in the supplied manifests (referenced at {field_path}).'
        suggestion = (
            f'Create a ConfigMap named "{cm_name}" in this file/set, or update the '
            f"reference to an existing ConfigMap, or mark it as optional: true "
            f"if it is intentionally absent."
        )

        return AnalysisResult(
            analyzer_name=self.name,
            rule_id=Rules.MISSING_CONFIGMAP_TARGET,
            severity="WARNING",
            message=message,
            resource_name=obj_name,
            resource_kind=doc.get("kind", ""),
            file_path="unknown",
            line_no=0,
            suggestion=suggestion,
        )

    def _check_container_envfrom(
        self,
        container: Dict[str, Any],
        defined_cm_names: Set[str],
        doc: Dict[str, Any],
        results: List[AnalysisResult],
    ) -> None:
        """Inspects envFrom blocks for missing ConfigMap references.

        Why: To catch bulk environment variable injection failures.
        """
        env_from = container.get("envFrom")
        if not isinstance(env_from, list):
            return

        for idx, item in enumerate(env_from):
            if not isinstance(item, dict):
                continue
            cm_ref = item.get("configMapRef")
            if not isinstance(cm_ref, dict):
                continue
            name = cm_ref.get("name")
            if not isinstance(name, str) or not name:
                continue
            if name not in defined_cm_names:
                field_path = f"spec.template.spec.containers[*].envFrom[{idx}].configMapRef.name"
                results.append(self._make_result(doc, name, field_path))

    def _check_container_env(
        self,
        container: Dict[str, Any],
        defined_cm_names: Set[str],
        doc: Dict[str, Any],
        results: List[AnalysisResult],
    ) -> None:
        """Inspects env blocks for missing ConfigMapKeyRef references.

        Why: To catch individual environment variable source failures.
        """
        env = container.get("env")
        if not isinstance(env, list):
            return

        for idx, item in enumerate(env):
            if not isinstance(item, dict):
                continue
            value_from = item.get("valueFrom")
            if not isinstance(value_from, dict):
                continue
            cm_key_ref = value_from.get("configMapKeyRef")
            if not isinstance(cm_key_ref, dict):
                continue
            name = cm_key_ref.get("name")
            if not isinstance(name, str) or not name:
                continue
            if name not in defined_cm_names:
                field_path = f"spec.template.spec.containers[*].env[{idx}].valueFrom.configMapKeyRef.name"
                results.append(self._make_result(doc, name, field_path))

    def _check_volumes(
        self,
        volumes: List[Dict[str, Any]],
        defined_cm_names: Set[str],
        doc: Dict[str, Any],
        results: List[AnalysisResult],
    ) -> None:
        """Inspects pod volumes for missing ConfigMap mounts.

        Why: To catch filesystem-based configuration binding failures.
        """
        for idx, vol in enumerate(volumes):
            if not isinstance(vol, dict):
                continue
            cm = vol.get("configMap")
            if not isinstance(cm, dict):
                continue
            name = cm.get("name")
            if not isinstance(name, str) or not name:
                continue
            if name not in defined_cm_names:
                field_path = f"spec.template.spec.volumes[{idx}].configMap.name"
                results.append(self._make_result(doc, name, field_path))
