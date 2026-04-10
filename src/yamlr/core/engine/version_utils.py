"""
Lightweight utilities for version detection.
Bypasses heavy engine imports for performance.
"""

import logging
import os
from typing import Optional

from yamlr.core.k8s_versions import MATRIX
from yamlr.core.k8s_versions import normalize_version as k8s_normalize

logger = logging.getLogger("yamlr.version")

__all__ = ["get_default_cluster_version", "normalize_version"]


def get_default_cluster_version(skip_detection: bool = False) -> str:
    """
    Intelligently determines the target Kubernetes version.
    Bypasses class-level imports of HealContext to maintain <100ms startup.
    """
    env_version = os.getenv("Yamlr_KUBE_VERSION")
    if env_version:
        return k8s_normalize(env_version)

    if not skip_detection:
        det = _detect_pro_version()
        if det:
            return det

    return f"v{MATRIX.default_recommended}"


def _detect_pro_version() -> Optional[str]:
    """Helper to detect version from Pro modules without blocking startup."""
    try:
        from yamlr.core.bridge import YamlrBridge

        if YamlrBridge.is_pro_enabled():
            mod = YamlrBridge.get_pro_module("cluster_detection")
            if mod and hasattr(mod, "ClusterDetection"):
                detector = YamlrBridge.get_cluster_detector("kubectl")
                if detector:
                    return detector.detect_from_kubectl() or detector.detect_from_cluster()
    except (ImportError, AttributeError):
        pass
    return None


def normalize_version(version: str) -> str:
    """Normalizes version string to vX.Y format using SSOT logic."""
    return k8s_normalize(version)
