"""
Reconciliation Registry - Default Rule Mappings
----------------------------------------------
Provides out-of-the-box mappings between external security findings
(Checkov, Kubeconform) and Yamlr SHIELD (SHD) rule IDs.

Why: Enables Complement Mode to auto-heal common security issues
     immediately without requiring manual user configuration.
"""

from __future__ import annotations

from typing import Dict, Optional


class ReconciliationRegistry:
    # Checkov ID to Yamlr Rule ID
    # Reference: https://docs.bridgecrew.io/docs/kubernetes-policy-index
    DEFAULT_CHECKOV_MAPPINGS: Dict[str, str] = {
        # HostPath Mounts (SHD-001)
        "CKV_K8S_1": "SHD-001",
        "CKV_K8S_37": "SHD-001",
        "CKV_K8S_43": "SHD-001",
        # Privileged / Root (SHD-002, SHD-016)
        "CKV_K8S_16": "SHD-002",  # privileged: true
        "CKV_K8S_21": "SHD-016",  # runAsNonRoot: false
        "CKV_K8S_20": "SHD-002",  # allowPrivilegeEscalation: true
        "CKV_K8S_38": "SHD-002",  # readOnlyRootFilesystem: false
        # Host Isolation (SHD-004)
        "CKV_K8S_40": "SHD-004",  # hostNetwork: true
        "CKV_K8S_41": "SHD-004",  # hostIPC: true
        "CKV_K8S_42": "SHD-004",  # hostPID: true
        # Resource Limits (SHD-005)
        "CKV_K8S_10": "SHD-005",  # resources: limits missing
        "CKV_K8S_11": "SHD-005",  # cpu limits missing
        "CKV_K8S_12": "SHD-005",  # memory limits missing
        # Network Policy (SHD-007)
        "CKV_K8S_18": "SHD-007",  # default-deny missing
        # Ingress (SHD-013)
        "CKV_K8S_5": "SHD-013",  # Ingress TLS missing
    }

    # Kubeconform snippet to Yamlr Rule ID
    DEFAULT_KUBECONFORM_MAPPINGS: Dict[str, str] = {
        "privileged": "SHD-002",
        "runasnonroot": "SHD-002",
        "hostpath": "SHD-001",
        "networkpolicy": "SHD-007",
        "limit": "SHD-005",
        "probe": "SHD-005",  # Resource/Availability
        "deprecated": "SHD-011",
    }

    @classmethod
    def get_checkov_mapping(cls, check_id: str) -> Optional[str]:
        return cls.DEFAULT_CHECKOV_MAPPINGS.get(check_id)

    @classmethod
    def get_kubeconform_mapping(cls, msg: str) -> Optional[str]:
        msg_lower = msg.lower()
        for snippet, rule_id in cls.DEFAULT_KUBECONFORM_MAPPINGS.items():
            if snippet in msg_lower:
                return rule_id
        return None
