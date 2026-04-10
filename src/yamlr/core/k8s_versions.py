from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

# Standardized API Versions
APPS_V1: str = "apps/v1"
RBAC_V1: str = "rbac.authorization.k8s.io/v1"


@dataclass(frozen=True)
class K8sSupportMatrix:
    """The Single Source of Truth for Kubernetes version support in Yamlr.

    Why: To avoid hardcoded versions across the CLI, catalogs, and docs,
         ensuring that bumping support is a one-line change.
    """

    min_supported: str = "1.21"
    max_supported: str = "1.31"
    default_recommended: str = "1.31"

    # Fully tested and bundled catalog versions
    supported_versions: List[str] = field(
        default_factory=lambda: "1.21 1.22 1.23 1.24 1.25 1.26 1.27 1.28 1.29 1.30 1.31".split()
    )

    # [ROUND-10] Standardized STABLE versions for core resources
    # Why: Used for heuristic validation when full catalog is unavailable.
    STABLE_VERSIONS: Dict[str, str] = field(
        default_factory=lambda: {
            "Deployment": APPS_V1,
            "Service": "v1",
            "Pod": "v1",
            "Ingress": "networking.k8s.io/v1",
            "StatefulSet": APPS_V1,
            "DaemonSet": APPS_V1,
            "Job": "batch/v1",
            "CronJob": "batch/v1",
            "Namespace": "v1",
            "Secret": "v1",
            "ConfigMap": "v1",
            "PersistentVolume": "v1",
            "PersistentVolumeClaim": "v1",
            "StorageClass": "storage.k8s.io/v1",
            "NetworkPolicy": "networking.k8s.io/v1",
            "Role": RBAC_V1,
            "ClusterRole": RBAC_V1,
            "RoleBinding": RBAC_V1,
            "ClusterRoleBinding": RBAC_V1,
            "HorizontalPodAutoscaler": "autoscaling/v2",
        }
    )


MATRIX = K8sSupportMatrix()


def get_default_version() -> str:
    """Returns the recommended default version for new manifests."""
    return MATRIX.default_recommended


def is_supported(version: str) -> bool:
    """Checks if a version has a dedicated bundled catalog."""
    v = version.lstrip("v").strip()
    # Handle minor version only (e.g. "1.31" in "1.31.2")
    parts = v.split(".")
    if len(parts) >= 2:
        v = f"{parts[0]}.{parts[1]}"
    return v in MATRIX.supported_versions


def is_stable(version: str) -> bool:
    """True if the version is a stable GA release (no alpha/beta/rc suffixes)."""
    v = str(version or "v1.31").strip().lower().lstrip("v")
    # Stable: 1.31, 1.31.0, 1.31.5
    # Unstable: 1.31.0-alpha.1, 1.31-beta, 1.31.0-rc.3
    # Logic: Stable should only contain numbers and dots.
    return bool(re.match(r"^\d+\.\d+(\.\d+)?$", v))


def normalize_version(version: str | None) -> str:
    """Ensures version is in 'vX.Y' format. Defaults to recommended if None."""
    if not version:
        return f"v{MATRIX.default_recommended}"

    v = str(version).strip().lower().lstrip("v")
    # Truncate patch version if present (e.g. 1.31.1 -> 1.31)
    parts = v.split(".")
    if len(parts) >= 2:
        v = f"{parts[0]}.{parts[1]}"

    return f"v{v}"


def closest_supported(version: str) -> str:
    """Finds the nearest supported version for 'best-effort' validation.

    Why: If a user targets a version outside our matrix, we want to provide
         the most relevant schema rather than failing or using a generic one.
    """
    v = version.lstrip("v").strip()
    parts = v.split(".")
    if len(parts) < 2:
        return MATRIX.default_recommended

    try:
        major = int(parts[0])
        minor = int(parts[1])
    except ValueError:
        return MATRIX.default_recommended

    # Convert supported list to numeric tuples for comparison
    numeric_supported = []
    for sv in MATRIX.supported_versions:
        sp = sv.split(".")
        numeric_supported.append((int(sp[0]), int(sp[1])))

    target = (major, minor)

    # If it's below our range, use the minimum
    min_v = numeric_supported[0]
    if target < min_v:
        return f"{min_v[0]}.{min_v[1]}"

    # If it's above our range, use the maximum
    max_v = numeric_supported[-1]
    if target > max_v:
        return f"{max_v[0]}.{max_v[1]}"

    # Otherwise, it must be in the middle but perhaps missing (e.g. a gap)
    # Return the largest supported version that is <= target
    best_match = min_v
    for sv in numeric_supported:
        if sv <= target:
            best_match = sv
        else:
            break

    return f"{best_match[0]}.{best_match[1]}"
