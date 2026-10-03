"""CIS Kubernetes Benchmark v1.8.0 Catalog Mapper.

Why: Enterprise security procurement teams demand compliance with industry
benchmarks (CIS v1.8 Section 5). This module maps native Yamlr forensic
detectors directly to official CIS benchmark items, establishing high rule
parity while powering automated lossless remediation.
"""
from typing import Any, Dict, List, Optional

CIS_RULES: Dict[str, Dict[str, Any]] = {
    "SEC-001": {
        "cis_id": "CIS-5.7.3",
        "section": "5.7.3",
        "title": "Apply Security Context to your Pods and Containers",
        "profile": "Level 1",
        "remediation": "Configure securityContext with non-root UID and restricted capabilities."
    },
    "SEC-002": {
        "cis_id": "CIS-5.2.2",
        "section": "5.2.2",
        "title": "Ensure ImagePullPolicy is set to Always for mutable tags",
        "profile": "Level 1",
        "remediation": "Set spec.containers[*].imagePullPolicy: Always or pin image by digest."
    },
    "SEC-003": {
        "cis_id": "CIS-5.4.1",
        "section": "5.4.1",
        "title": "Prefer using secrets as files over environment variables",
        "profile": "Level 1",
        "remediation": "Mount sensitive configurations as volume mounts instead of env variables."
    },
    "SEC-006": {
        "cis_id": "CIS-5.1.1",
        "section": "5.1.1",
        "title": "Minimize the admission of privileged containers",
        "profile": "Level 1",
        "remediation": "Set spec.containers[*].securityContext.privileged: false."
    },
    "SEC-007": {
        "cis_id": "CIS-5.1.4",
        "section": "5.1.4",
        "title": "Minimize the admission of containers wishing to share the host network namespace",
        "profile": "Level 1",
        "remediation": "Set spec.hostNetwork: false."
    },
    "SEC-008": {
        "cis_id": "CIS-5.1.2",
        "section": "5.1.2",
        "title": "Minimize the admission of containers wishing to share the host process ID namespace",
        "profile": "Level 1",
        "remediation": "Set spec.hostPID: false."
    },
    "SEC-009": {
        "cis_id": "CIS-5.1.3",
        "section": "5.1.3",
        "title": "Minimize the admission of containers wishing to share the host IPC namespace",
        "profile": "Level 1",
        "remediation": "Set spec.hostIPC: false."
    },
    "SEC-010": {
        "cis_id": "CIS-5.1.5",
        "section": "5.1.5",
        "title": "Minimize the admission of containers with allowPrivilegeEscalation",
        "profile": "Level 1",
        "remediation": "Set spec.containers[*].securityContext.allowPrivilegeEscalation: false."
    },
    "SEC-011": {
        "cis_id": "CIS-5.1.6",
        "section": "5.1.6",
        "title": "Minimize the admission of root containers",
        "profile": "Level 1",
        "remediation": "Set spec.securityContext.runAsNonRoot: true."
    },
    "SEC-012": {
        "cis_id": "CIS-5.2.5",
        "section": "5.2.5",
        "title": "Minimize the admission of containers with read-only root file system",
        "profile": "Level 2",
        "remediation": "Set spec.containers[*].securityContext.readOnlyRootFilesystem: true."
    },
    "NET-001": {
        "cis_id": "CIS-5.3.1",
        "section": "5.3.1",
        "title": "Ensure Network Policies are defined for all namespaces",
        "profile": "Level 1",
        "remediation": "Create NetworkPolicy resources specifying allowed ingress and egress flows."
    },
    "NET-004": {
        "cis_id": "CIS-5.7.1",
        "section": "5.7.1",
        "title": "Create administrative boundaries between resources using namespaces",
        "profile": "Level 1",
        "remediation": "Avoid deploying resources in default namespace; specify metadata.namespace."
    }
}


def get_cis_mapping(detector_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the CIS Benchmark entry for a given Yamlr detector ID."""
    return CIS_RULES.get(detector_id.upper())


def get_cis_tag(detector_id: str) -> Optional[str]:
    """Returns the CIS rule identifier (e.g. 'CIS-5.1.1') if mapped."""
    entry = CIS_RULES.get(detector_id.upper())
    return entry.get("cis_id") if entry else None


def list_cis_rules() -> List[Dict[str, Any]]:
    """Returns all mapped CIS Kubernetes Benchmark rules."""
    return list(CIS_RULES.values())
