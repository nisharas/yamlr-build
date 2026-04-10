#!/usr/bin/env python3
"""
Yamlr REMEDIATION REGISTRY
--------------------------
The "Policy-to-Heal" bridge for EPIC-24.

Why: Maps external policy violation IDs (Kyverno, OPA, Checkov) to
     specific Yamlr mutation functions. This transforms Yamlr from
     a reporter into an automated surgeon for 3rd party findings.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger("yamlr.remediation")
__all__ = ["RemediationRegistry"]


class RemediationRegistry:
    """
    Central registry for mapping external tool rules to Yamlr mutations.
    """

    # Mapping Format: { "tool/policy/rule": "internal_fix_id" }
    _MAPPING = {
        # ⚖️ Forensic Mappings (SHIELD Engine)
        "SHD-001": None,  # Unsafe HostPath (Report Only)
        "SHD-002": "disallow_privileged",  # Privileged Container
        "SHD-003": None,  # Sensitive Volume Exposure
        "SHD-004": None,  # Host Network/PID/IPC
        "SHD-005": "enforce_resource_limits",  # Resource Starvation
        "SHD-016": "enforce_non_root",  # Root Execution Risk
        # 🧩 Canonical Mappings (Yamlr Core Rules)
        "rule/privileged-container": "disallow_privileged",
        "rule/run-as-root": "enforce_non_root",
        "rule/allow-privilege-escalation": "enforce_non_root",
        "rule/unsafe-hostpath": None,
        "rule/host-network": None,
        "rule/ingress-tls-missing": "enforce_readonly_root_fs",  # Simplified forensic fix
        "rule/resource-limits": "enforce_resource_limits",
        # 🔗 Legacy / Compatibility Mappings
        "security/run-as-non-root": "enforce_non_root",
        "security/privileged-container": "disallow_privileged",
        "security/read-only-root-filesystem": "enforce_readonly_root_fs",
        "resources/cpu-limit-missing": "enforce_resource_limits",
        "resources/memory-limit-missing": "enforce_resource_limits",
    }

    _REGEX_MAPPING = {
        r"kyverno/.*-privileged-.*": "disallow_privileged",
        r"kyverno/.*-labels/.*": "inject_required_labels",
        r"opa/k8srequired.*": "enforce_resource_limits",
    }

    _MUTATION_MAP = {}

    @classmethod
    def _get_mutation_map(cls):
        """Lazy-loads mutation functions to avoid circular dependencies."""
        if not cls._MUTATION_MAP:
            try:
                from yamlr.healers.best_practices.privilege_escalation import (
                    disallow_privileged,
                    drop_all_capabilities,
                    enforce_non_root,
                    enforce_readonly_root_fs,
                )
                from yamlr.healers.best_practices.resources import enforce_resource_limits

                cls._MUTATION_MAP = {
                    "enforce_non_root": enforce_non_root,
                    "disallow_privileged": disallow_privileged,
                    "enforce_readonly_root_fs": enforce_readonly_root_fs,
                    "drop_all_capabilities": drop_all_capabilities,
                    "enforce_resource_limits": enforce_resource_limits,
                    "security_hardening": drop_all_capabilities,
                }
            except ImportError as e:
                logger.error(f"Failed to load mutation functions: {e}")
                cls._MUTATION_MAP = {}
        return cls._MUTATION_MAP

    @classmethod
    def get_fix_id(cls, rule_id: str) -> Optional[str]:
        """Translates an external Rule ID to a Yamlr Fix ID."""
        if not rule_id:
            return None
        if rule_id in cls._MAPPING:
            return cls._MAPPING[rule_id]

        # Regex match
        for pattern, internal_id in cls._REGEX_MAPPING.items():
            if re.match(pattern, rule_id, re.IGNORECASE):
                return internal_id

        # Heuristic/Partial match
        rule_lower = rule_id.lower()
        for ext_id, internal_id in cls._MAPPING.items():
            if ext_id.lower() in rule_lower:
                return internal_id

        return None

    @classmethod
    def get_mutation_fn(cls, fix_id: str):
        """Returns the actual mutation function for a given Fix ID."""
        return cls._get_mutation_map().get(fix_id)

    @classmethod
    def register_manual_mapping(cls, external_id: str, internal_id: str):
        """Allows users/admins to extend the mapping at runtime."""
        cls._MAPPING[external_id] = internal_id
