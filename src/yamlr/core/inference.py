"""
Yamlr VERSION INFERENCE ENGINE
------------------------------
Automatically detects the most appropriate Kubernetes version for a workspace
by analyzing the 'apiVersion' fields across all manifests.

Why: To eliminate manual version-locking and ensure validation is always
     aligned with the actually used APIs in the repository.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Set

logger = logging.getLogger("yamlr.inference")


class VersionInferenceError(Exception):
    """Raised when K8s version inference is ambiguous or impossible."""

    pass


class VersionInferenceEngine:
    """
    Analyzes a collection of manifests to determine the target K8s version.

    Heuristics:
    1. Scan manifests for 'apiVersion' while ignoring non-K8s CRDs.
    2. Map APIs to the K8s version they were introduced/stabilized in.
    3. Detect version conflicts (e.g., manifest A requires 1.14, manifest B requires 1.25).
    4. Select the highest required version as the target, or refuse if ambiguous.
    """

    # Comprehensive mapping of apiVersion -> Minimum K8s Version
    API_TO_K8S_MAP = {
        # Core & Apps
        "apps/v1": "v1.16",
        "batch/v1": "v1.21",
        "batch/v1beta1": "v1.8",
        # Networking
        "networking.k8s.io/v1": "v1.22",
        "networking.k8s.io/v1beta1": "v1.14",
        "extensions/v1beta1": "v1.8",  # Deprecated long ago
        # Policy & RBAC
        "policy/v1": "v1.21",
        "policy/v1beta1": "v1.10",
        "rbac.authorization.k8s.io/v1": "v1.8",
        # Autoscaling & Storage
        "autoscaling/v2": "v1.23",
        "autoscaling/v2beta2": "v1.12",
        "storage.k8s.io/v1": "v1.13",
        # Newer APIs
        "gateway.networking.k8s.io/v1": "v1.24",
        "admissionregistration.k8s.io/v1": "v1.16",
    }

    def infer_version(self, manager: "YamlrManager", targets: List[str] = None) -> str:
        """
        Executes the inference logic across the provided targets.

        Why: To automatically align the healing engine with the workspace's target K8s version.
        """
        from yamlr.core.config import ConfigManager

        fallback = getattr(ConfigManager, "DEFAULT_INFERENCE_FALLBACK_VERSION", "v1.28")
        if not targets:
            targets = ["."]

        # 1. Faster Bypasses (Env / Live Cluster)
        pre_infer = self._get_pre_inference_version(manager.kubectl_path)
        if pre_infer:
            return pre_infer

        # 2. Heuristic Sampling
        detected_apis: Set[str] = set()
        self._sample_apis_from_targets(manager, targets, detected_apis)

        if not detected_apis:
            logger.debug(f"Inference: No APIs detected. Falling back to {fallback}")
            return fallback

        # 3. Mapping & Validation
        required_versions = self._map_apis_to_versions(detected_apis)
        if not required_versions:
            logger.debug(f"Inference: No recognized K8s APIs in {detected_apis}. Falling back to {fallback}")
            return fallback

        # 4. Conflict Resolution & Final Selection
        return self._resolve_final_version(required_versions)

    def _get_pre_inference_version(self, kubectl_path: str) -> Optional[str]:
        """Checks for prioritized version overrides before deep scanning."""
        import os
        from yamlr.core.bridge import YamlrBridge
        from yamlr.core.k8s_versions import normalize_version

        # Priority 1: Environment Override
        env_v = os.getenv("YAMLR_KUBE_VERSION")
        if env_v:
            return normalize_version(env_v)

        # Priority 2: Live Cluster Probe (PRO)
        detector = YamlrBridge.get_cluster_detector(kubectl_path=kubectl_path)
        if detector:
            live_version = detector.detect_server_version()
            if live_version:
                logger.debug(f"Inference: Live cluster auto-detected K8s {live_version}")
                return live_version
        return None

    def _sample_apis_from_targets(self, manager: "YamlrManager", targets: List[str], api_set: Set[str]):
        """Crawl workspace targets to sample used apiVersions."""
        extensions = [".yaml", ".yml"]
        sample_count = 0
        max_samples = 50

        for target in targets:
            target_path = manager.workspace / target
            if not target_path.exists():
                continue

            if target_path.is_file():
                self._extract_apis_from_file(target_path, api_set)
            else:
                for _, rel_p in manager.fs.crawl(target_path, extensions, max_depth=5):
                    self._extract_apis_from_file(manager.workspace / rel_p, api_set)
                    sample_count += 1
                    if sample_count >= max_samples:
                        break
            if sample_count >= max_samples:
                break

    def _map_apis_to_versions(self, apis: Set[str]) -> Dict[str, str]:
        """Maps detected apiVersions to their minimum required K8s versions."""
        required: Dict[str, str] = {}
        for api in apis:
            if self._is_k8s_api(api):
                version = self.API_TO_K8S_MAP.get(api)
                if version:
                    required[api] = version
        return required

    def _resolve_final_version(self, required_versions: Dict[str, str]) -> str:
        """Resolves the final target version from multiple requirements."""
        unique_versions = sorted(set(required_versions.values()), key=self._version_key)

        if len(unique_versions) > 1:
            if self._get_version_spread(unique_versions) > 3:
                msg = (
                    f"Ambiguous K8s version detected: Manifests require multiple versions "
                    f"ranging from {unique_versions[0]} to {unique_versions[-1]}. "
                    f"Please use --kube-version to lock a specific version."
                )
                logger.error(f"❌ {msg}")
                raise VersionInferenceError(msg)

            logger.warning(
                f"⚠️  Inference: Detected mixed API requirements ({', '.join(unique_versions)}). "
                f"Falling back to highest common denominator: {unique_versions[-1]}"
            )

        target = unique_versions[-1]
        logger.info(
            f"🎯 Inference: Targeted K8s [bold green]{target}[/bold green] based on {len(required_versions)} core API signatures."
        )
        return target

    def _is_k8s_api(self, api: str) -> bool:
        """Determines if an apiVersion string belongs to a standard K8s group."""
        if "/" not in api:
            return True  # Core group (v1)

        group = api.split("/")[0]
        known_groups = {
            "apps",
            "batch",
            "networking.k8s.io",
            "policy",
            "rbac.authorization.k8s.io",
            "admissionregistration.k8s.io",
            "autoscaling",
            "storage.k8s.io",
            "scheduling.k8s.io",
            "node.k8s.io",
            "extensions",
            "certificates.k8s.io",
            "coordination.k8s.io",
        }
        return group in known_groups or group.endswith(".k8s.io")

    def _get_version_spread(self, versions: List[str]) -> int:
        """Calculates the minor version spread between oldest and newest detected versions."""
        v_keys = [self._version_key(v) for v in versions]
        return v_keys[-1][1] - v_keys[0][1]

    def _version_key(self, v: str) -> List[int]:
        """Semver-lite sorting key."""
        parts = v.lstrip("v").split(".")
        return [int(p) for p in parts]

    def _extract_apis_from_file(self, path: Path, api_set: Set[str]):
        """Fast extraction of apiVersion using regex to avoid full YAML parsing."""
        try:
            # We only need the first few lines usually
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(4096)

            # Regex to find apiVersion: <value>
            matches = re.finditer(r"apiVersion:\s*([^\s#]+)", content)
            for match in matches:
                api_set.add(match.group(1).strip("'\""))
        except Exception:
            pass
