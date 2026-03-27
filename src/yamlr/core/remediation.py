#!/usr/bin/env python3
"""
Yamlr REMEDIATION REGISTRY
--------------------------
The "Policy-to-Heal" bridge for EPIC-24.

Why: Maps external policy violation IDs (Kyverno, OPA, Checkov) to 
     specific Yamlr mutation functions. This transforms Yamlr from 
     a reporter into an automated surgeon for 3rd party findings.

Architecture:
- Pure logic (Transformation tier).
- Registry pattern for pluggable remediation mapping.
"""

from __future__ import annotations
import logging
import re
from typing import Optional

logger = logging.getLogger("yamlr.remediation")
__all__ = ['RemediationRegistry']


class RemediationRegistry:
    """
    Central registry for mapping external tool rules to Yamlr mutations.
    """
    
    # Mapping Format: { "tool/policy/rule": "internal_fix_id" }
    _MAPPING = {
        # Kyverno Standard Policies
        "kyverno/disallow-privileged-containers/privileged-containers": "disallow_privileged",
        "kyverno/require-labels/check-labels": "inject_required_labels",
        "kyverno/disallow-default-namespace/validate-namespace": "enforce_namespace",
        "kyverno/require-resources/validate-resource-limits": "enforce_resource_limits",
        "kyverno/require-ro-rootfs/validate-readonly-root-filesystem": "enforce_readonly_root_fs",
        "kyverno/require-run-as-non-root/run-as-non-root": "enforce_non_root",
        
        # OPA/Gatekeeper Standard Policies (Library)
        "opa/k8srequiredlabels": "inject_required_labels",
        "opa/k8sprivilegedcontainer": "disallow_privileged",
        "opa/k8sallowedrepos": "enforce_trusted_registries",
        "opa/k8srequiredresources": "enforce_resource_limits",
        "opa/k8sblockwildcardingress": "fix_ingress_host",
        "kyverno/k8sblockwildcardingress/wildcard-ingress": "fix_ingress_host",
        
        # Checkov / Terrascan / Generic
        "CKV_K8S_16": "enforce_readonly_root_fs",
        "CKV_K8S_21": "enforce_non_root",
        
        # Standalone Rule IDs (Common in custom OPA packs)
        "disallow_privileged": "disallow_privileged",
        "require_labels": "inject_required_labels",
        "enforce_namespace": "enforce_namespace",
    }
    
    # Regex-based mappings for dynamic IDs
    _REGEX_MAPPING = {
        r"kyverno/.*-privileged-.*": "disallow_privileged",
        r"kyverno/.*-labels/.*": "inject_required_labels",
        r"opa/k8srequired.*": "enforce_resource_limits",
    }

    @classmethod
    def get_fix_id(cls, rule_id: str) -> Optional[str]:
        """
        Translates an external Rule ID to a Yamlr Fix ID.
        
        Why: Decouples external policy names from internal healing logic.
        """
        if not rule_id:
            return None

        # 1. Exact match
        if rule_id in cls._MAPPING:
            return cls._MAPPING[rule_id]
            
        # 2. Regex match
        for pattern, internal_id in cls._REGEX_MAPPING.items():
            if re.match(pattern, rule_id, re.IGNORECASE):
                return internal_id

        # 3. Partial match (heuristic)
        rule_lower = rule_id.lower()
        for ext_id, internal_id in cls._MAPPING.items():
            if ext_id.lower() in rule_lower:
                return internal_id
                
        return None

    @classmethod
    def register_manual_mapping(cls, external_id: str, internal_id: str):
        """Allows users/admins to extend the mapping at runtime."""
        cls._MAPPING[external_id] = internal_id
