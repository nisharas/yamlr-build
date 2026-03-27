#!/usr/bin/env python3
"""
Yamlr OSS – DEPRECATION ENGINE
-----------------------------
Static detection of deprecated and removed Kubernetes APIs.

Why: Version intelligence is a core Safety Engine pillar.
     Deploying with a removed API silently fails — the resource
     is simply ignored by the cluster. This is a top-3 K8s
     deployment failure category.
"""

from __future__ import annotations
import logging
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("yamlr.deprecations")

__all__ = ["DeprecationInfo", "DeprecationChecker"]

@dataclass(frozen=True)
class DeprecationInfo:
    """
    Metadata describing a deprecated or removed Kubernetes API.

    Why: Encapsulates regulatory versioning data used by both the 
         analyzer (for detection) and the UI (for remediation advice).
    """
    deprecated_api: str
    replacement_api: str
    deprecated_in_version: str
    removed_in_version: str
    kind: str
    severity: str  # WARNING | REMOVED
    migration_notes: str
    strategy: str = "NONE"

class DeprecationChecker:
    """Kubernetes API deprecation and field-level change detector.

    Why: Version intelligence is the second pillar of the Safety Engine.
         Deploying with removed APIs silently fails — the resource is
         ignored by the cluster with no error. This is a top-3 K8s
         deployment failure category.
    """

    def __init__(self):
        """Initialize OSS deprecation checker by loading JSON data."""
        self._deprecated_apis: Dict[Tuple[str, str], DeprecationInfo] = {}
        self._deprecated_fields: Dict[Tuple[str, str], Dict] = {}
        self._load_data()

    def _load_data(self):
        """Loads deprecation data from JSON file."""
        try:
            data_path = os.path.join(os.path.dirname(__file__), "..", "data", "k8s_deprecations.json")
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Load APIs
                for item in data.get("apis", []):
                    # Default values for missing fields to ensure compatibility
                    deprecated_api = item.get("deprecated_api")
                    kind = item.get("kind")
                    if deprecated_api and kind:
                        self._deprecated_apis[(deprecated_api, kind)] = DeprecationInfo(
                            deprecated_api=deprecated_api,
                            replacement_api=item.get("replacement_api", "N/A"),
                            deprecated_in_version=item.get("deprecated_in_version", "1.0"),
                            removed_in_version=item.get("removed_in_version", "1.0"),
                            kind=kind,
                            severity=item.get("severity", "WARNING"),
                            migration_notes=item.get("migration_notes", ""),
                            strategy=item.get("strategy", "NONE")
                        )
                
                # Load Fields
                fields_data = data.get("fields", {})
                for kind, paths in fields_data.items():
                    for path, info in paths.items():
                        self._deprecated_fields[(kind, path)] = info
                        
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load deprecation data: {e}")

    def check(self, api_version: str, kind: str) -> Optional[DeprecationInfo]:
        """Check if a specific API version/kind combination is deprecated."""
        return self._deprecated_apis.get((api_version, kind))

    def list_all(self) -> List[DeprecationInfo]:
        """Return all known deprecation entries."""
        return list(self._deprecated_apis.values())

    def is_removed(self, api_version: str, kind: str, target_version: str) -> bool:
        """Check if an API is removed in a specific K8s version."""
        info = self.check(api_version, kind)
        if not info or info.severity != "REMOVED":
            return False
        return self._compare_versions(target_version, info.removed_in_version) >= 0

    def check_field(self, kind: str, field_path: str) -> Optional[Dict]:
        """Check if a specific field is deprecated."""
        return self._deprecated_fields.get((kind, field_path))

    def upgrade_risk_score(self, from_version: str, to_version: str) -> Dict:
        """Calculate risk score for upgrading between K8s versions."""
        removals = []
        warnings = []

        for info in self._deprecated_apis.values():
            removed_version = info.removed_in_version
            if info.severity == "REMOVED":
                if (self._compare_versions(removed_version, from_version) > 0 and 
                    self._compare_versions(removed_version, to_version) <= 0):
                    removals.append(info)
            elif info.severity == "WARNING":
                dep_version = info.deprecated_in_version
                if (self._compare_versions(dep_version, from_version) > 0 and 
                    self._compare_versions(dep_version, to_version) <= 0):
                    warnings.append(info)

        risk_level = "HIGH" if len(removals) >= 3 else "MEDIUM" if len(removals) >= 1 else "LOW" if len(warnings) >= 1 else "NONE"

        return {
            "from_version": from_version,
            "to_version": to_version,
            "risk_level": risk_level,
            "removal_count": len(removals),
            "warning_count": len(warnings),
            "removals": [{"api": r.deprecated_api, "kind": r.kind, "removed_in": r.removed_in_version} for r in removals],
            "warnings": [{"api": w.deprecated_api, "kind": w.kind, "deprecated_in": w.deprecated_in_version} for w in warnings],
        }

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare K8s versions safely."""
        try:
            v1_clean = v1.lstrip("v").rstrip("+")
            v2_clean = v2.lstrip("v").rstrip("+")
            v1_parts = [int(x) for x in v1_clean.split(".")[:2]]
            v2_parts = [int(x) for x in v2_clean.split(".")[:2]]

            if v1_parts[0] != v2_parts[0]:
                return 1 if v1_parts[0] > v2_parts[0] else -1
            if v1_parts[1] != v2_parts[1]:
                return 1 if v1_parts[1] > v2_parts[1] else -1
            return 0
        except (ValueError, IndexError) as e:
            logger.warning(f"Version comparison failed: {v1} vs {v2}: {e}")
            return 0
