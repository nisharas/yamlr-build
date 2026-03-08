#!/usr/bin/env python3
"""
Yamlr STABILIZER - The K8s Normalizer
-------------------------------------
Extracts semantic normalization logic from the Structurer.
Focuses on "Stabilizing" manifests by fixing common structural errors.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-13
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("yamlr.healers.stabilizer")

class K8sStabilizer:
    """
    Stabilizes Kubernetes manifests by normalizing common structural issues.
    """

    @staticmethod
    def normalize_resources(container: dict) -> None:
        """Canonicalize container.resources structure."""
        if not isinstance(container, dict):
            return

        res = container.get("resources")
        if res is None:
            return

        if not isinstance(res, dict):
            if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict):
                res = res[0]
                container["resources"] = res
            else:
                res = {}
                container["resources"] = res

        requests = res.get("requests")
        if not isinstance(requests, dict):
            requests = {}
            res["requests"] = requests

        if "cpu" in res:
            requests.setdefault("cpu", res.pop("cpu"))
        if "memory" in res:
            requests.setdefault("memory", res.pop("memory"))

        limits = res.get("limits")
        if not isinstance(limits, dict):
            limits = {}
            res["limits"] = limits

    @staticmethod
    def normalize_envfrom(container: dict) -> None:
        """Fix envFrom blocks and lift misnested fields."""
        if not isinstance(container, dict):
            return

        env_from = container.get("envFrom")
        if not env_from:
            return

        if isinstance(env_from, dict):
            env_from = [env_from]
            container["envFrom"] = env_from

        if not isinstance(env_from, list):
            return

        for item in env_from:
            if not isinstance(item, dict):
                continue

            for key in ("ports", "readinessProbe", "livenessProbe", "resources"):
                if key in item and key not in container:
                    container[key] = item.pop(key)

            if "configMapRef" in item:
                ref = item.get("configMapRef")
                if ref is None or not isinstance(ref, dict):
                    ref = {}
                if "name" in item and "name" not in ref:
                    ref["name"] = item.pop("name")
                item["configMapRef"] = ref

            if "secretRef" in item:
                ref = item.get("secretRef")
                if ref is None or not isinstance(ref, dict):
                    ref = {}
                if "name" in item and "name" not in ref:
                    ref["name"] = item.pop("name")
                item["secretRef"] = ref

    @staticmethod
    def normalize_metadata(doc: dict) -> bool:
        """Moves orphan 'name' or 'namespace' keys into 'metadata'."""
        if not isinstance(doc, dict):
            return False

        modified = False
        orphan_keys = [k for k in ("name", "namespace", "labels") if k in doc and k != "metadata"]
        
        if not orphan_keys and "metadata" not in doc:
            return False

        if "metadata" not in doc:
            doc["metadata"] = {}
            modified = True

        metadata = doc["metadata"]
        if not isinstance(metadata, dict):
            metadata = {}
            doc["metadata"] = metadata
            modified = True

        for key in ("name", "namespace", "labels"):
            if key in doc and key != "metadata":
                val = doc.pop(key)
                if key not in metadata or not metadata[key]:
                    metadata[key] = val
                    modified = True

        return modified

    @staticmethod
    def normalize_deployment_selector(doc: dict) -> None:
        """Ensure spec.selector matches spec.template.metadata.labels."""
        if not isinstance(doc, dict):
            return

        kind = str(doc.get("kind") or "").lower()
        api_version = str(doc.get("apiVersion") or "").lower()
        if kind != "deployment" or not api_version.startswith("apps/"):
            return

        spec = doc.get("spec")
        if not isinstance(spec, dict) or "selector" in spec:
            return

        template = spec.get("template")
        if not isinstance(template, dict):
            return
        t_meta = template.get("metadata")
        if not isinstance(t_meta, dict):
            return
        t_labels = t_meta.get("labels")
        if not isinstance(t_labels, dict) or not t_labels:
            return

        owner_keys = ["app.kubernetes.io/name", "app", "deployment"]
        inferred = {}
        for key in owner_keys:
            if key in t_labels:
                inferred[key] = t_labels[key]
                break

        if not inferred:
            inferred = dict(t_labels)

        spec["selector"] = {"matchLabels": inferred}
        spec.pop("__selector_was_here", None)
