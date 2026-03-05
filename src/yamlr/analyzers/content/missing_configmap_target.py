from typing import Any, Dict, List, Set

from yamlr.analyzers.base import BaseAnalyzer, AnalysisResult
from yamlr.analyzers.rules import Rules
from yamlr.core.scoring import Severity  # same Severity type you already use


class MissingConfigMapTargetAnalyzer(BaseAnalyzer):
    """
    Detect references to ConfigMaps (envFrom/env/volumes) that
    are not defined in the current manifest set.
    """
   
    @property
    def name(self) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return "missing-configmap-target"

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
        results: List[AnalysisResult] = []

        defined_cm_names = self._collect_configmaps(docs)

        for doc in docs:
            kind = (doc.get("kind") or "").lower()
            if kind not in {
                "deployment",
                "statefulset",
                "daemonset",
                "job",
                "cronjob",
                "replicaset",
            }:
                continue

            spec = doc.get("spec") or {}
            template = spec.get("template") or {}
            if not isinstance(template, dict):
                continue

            pod_spec = template.get("spec") or {}
            if not isinstance(pod_spec, dict):
                continue

            containers = pod_spec.get("containers") or []
            if isinstance(containers, list):
                for c in containers:
                    if not isinstance(c, dict):
                        continue
                    self._check_container_envfrom(
                        c, defined_cm_names, doc, results
                    )
                    self._check_container_env(
                        c, defined_cm_names, doc, results
                    )

            volumes = pod_spec.get("volumes") or []
            if isinstance(volumes, list):
                self._check_volumes(volumes, defined_cm_names, doc, results)

        return results

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _collect_configmaps(self, docs: List[Dict[str, Any]]) -> Set[str]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
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
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        meta = doc.get("metadata") or {}
        obj_name = meta.get("name", "<unknown>")

        message = (
            f'ConfigMap "{cm_name}" is not defined in the supplied manifests '
            f'(referenced at {field_path}).'
        )
        suggestion = (
            f'Create a ConfigMap named "{cm_name}" in this file/set, or update the '
            f'reference to an existing ConfigMap, or mark it as optional: true '
            f'if it is intentionally absent.'
        )

        return AnalysisResult(
            analyzer_name=self.name,
            rule_id=Rules.MISSING_CONFIGMAP_TARGET,
            severity="WARNING",
            message=message,
            resource_name=obj_name,
            resource_kind=doc.get("kind", ""),
            file_path="unknown",        # or actual path if you can wire it through
            line_number=0,
            suggestion=suggestion,
        )


    def _check_container_envfrom(
        self,
        container: Dict[str, Any],
        defined_cm_names: Set[str],
        doc: Dict[str, Any],
        results: List[AnalysisResult],
    ) -> None:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
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
                field_path = (
                    f"spec.template.spec.containers[*].envFrom[{idx}]."
                    f"configMapRef.name"
                )
                results.append(self._make_result(doc, name, field_path))

    def _check_container_env(
        self,
        container: Dict[str, Any],
        defined_cm_names: Set[str],
        doc: Dict[str, Any],
        results: List[AnalysisResult],
    ) -> None:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
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
                field_path = (
                    f"spec.template.spec.containers[*].env[{idx}]."
                    f"valueFrom.configMapKeyRef.name"
                )
                results.append(self._make_result(doc, name, field_path))

    def _check_volumes(
        self,
        volumes: List[Dict[str, Any]],
        defined_cm_names: Set[str],
        doc: Dict[str, Any],
        results: List[AnalysisResult],
    ) -> None:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
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
                field_path = (
                    f"spec.template.spec.volumes[{idx}].configMap.name"
                )
                results.append(self._make_result(doc, name, field_path))
