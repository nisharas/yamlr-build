#!/usr/bin/env python3
"""
Yamlr PRIVILEGE ESCALATION AUDITOR - Forensic Security Analysis
---------------------------------------------------------------
Detects and remediates privilege escalation risks in Kubernetes Pods and Containers.

Why: Misconfigured securityContexts and dangerous capabilities are the
     primary vector for container escape and host takeover.
"""

from __future__ import annotations

import logging
from typing import Any, List

from yamlr.analyzers.base import AnalysisResult
from yamlr.analyzers.rules import Rules
from yamlr.core.k8s_utils import extract_containers, find_pod_spec

logger = logging.getLogger("yamlr.healers.best_practices.privilege_escalation")


class PrivilegeEscalationAuditor:
    """
    Forensic auditor for Pod and Container securityContexts.
    """

    DANGEROUS_CAPS = {
        "SYS_ADMIN",
        "NET_ADMIN",
        "SYS_PTRACE",
        "SYS_MODULE",
        "DAC_READ_SEARCH",
        "DAC_OVERRIDE",
        "SYS_RAWIO",
        "SYS_TIME",
        "CHOWN",
        "FOWNER",
        "SETUID",
        "SETGID",
    }

    SENSITIVE_PATHS = {
        "/proc",
        "/sys",
        "/var/run/docker.sock",
        "/var/lib/docker",
        "/etc/shadow",
        "/etc/passwd",
        "/var/run/kubernetes",
    }

    def __init__(self):
        self.name = "PrivilegeEscalationAuditor"

    def scan_doc(self, doc: Any, fpath: str = "unknown") -> List[AnalysisResult]:
        """
        Scans a document for privilege escalation risks without modifying it.
        """
        if not hasattr(doc, "get"):
            return []

        kind = doc.get("kind", "")
        pod_spec = find_pod_spec(doc)
        if not pod_spec:
            return []

        findings: List[AnalysisResult] = []
        name = doc.get("metadata", {}).get("name", "unnamed")

        # 1. Audit Pod Level
        self._audit_pod_level(pod_spec, kind, name, fpath, findings)

        # 2. Audit Containers
        containers = extract_containers(doc)
        with open("d:\\yamlr\\pe_debug.log", "a") as f:
            f.write(f"DEBUG: Scanned {kind}/{name}, containers={len(containers)}\n")
        for c in containers:
            if not hasattr(c, "get"):
                continue
            self._audit_container(c, kind, name, fpath, findings)

        # 3. Audit Volumes
        self._audit_volumes(pod_spec, kind, name, fpath, findings)

        with open("d:\\yamlr\\pe_debug.log", "a") as f:
            f.write(f"DEBUG: scan_doc found {len(findings)} findings\n")
            for find in findings:
                f.write(f"DEBUG: Finding Rule={find.rule_id} Msg={find.message}\n")
        return findings

    def heal_doc(self, doc: Any, context: Any = None, harden: bool = False) -> bool:
        """
        Audits security contexts and attaches findings.
        Returns True if auto-remediations are applied (S2: Apply).
        """
        fpath = doc.get("__file_path__", "unknown") if hasattr(doc, "get") else "unknown"
        findings = self.scan_doc(doc, fpath=fpath)

        if findings and context and hasattr(context, "add_finding"):
            for f in findings:
                context.add_finding(f)

        # 4. Apply Remediation (S2: Apply)
        modified = False
        if harden:
            modified = self._remediate(doc)

        if findings and context and hasattr(context, "add_finding"):
            for f in findings:
                context.add_finding(f)

        return modified

    def _audit_pod_level(self, pod_spec: dict, kind: str, name: str, fpath: str, findings: List[AnalysisResult]):
        sc = pod_spec.get("securityContext") or {}

        # 1. Root at Pod Level
        if sc.get("runAsNonRoot") is False or sc.get("runAsUser") == 0:
            findings.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    rule_id=Rules.RUN_AS_ROOT,
                    severity="critical",
                    message=f"Pod {kind}/{name} allows running as root (runAsUser: 0 or runAsNonRoot: false).",
                    resource_name=name,
                    resource_kind=kind,
                    file_path=fpath,
                    suggestion="Set 'runAsNonRoot: true' and 'runAsUser' to a non-zero value.",
                    impact_description="Running as root inside a container significantly increases the risk if a container escape occurs.",
                    rationale="Principal of least privilege requires running as a non-privileged user.",
                    risk_level="CRITICAL",
                )
            )

        # 3. hostPath Volumes
        volumes = pod_spec.get("volumes", [])
        for vol in volumes:
            if "hostPath" in vol:
                hp = vol["hostPath"]
                path = hp.get("path", "unspecified")
                findings.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id=Rules.UNSAFE_HOSTPATH,
                        severity="critical",
                        message=f"Pod {kind}/{name} mounts hostPath: {path}, bypassing filesystem isolation.",
                        resource_name=name,
                        resource_kind=kind,
                        file_path=fpath,
                        impact_description=f"Using hostPath allows the container to access and potentially modify sensitive files on the host node ({path}).",
                        risk_level="HIGH",
                    )
                )

    def _audit_container(self, container: dict, kind: str, name: str, fpath: str, findings: List[AnalysisResult]):
        c_name = container.get("name", "unnamed")
        sc = container.get("securityContext") or {}

        # 1. Privileged Mode
        if sc.get("privileged") is True:
            findings.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    rule_id=Rules.PRIVILEGED_CONTAINER,
                    severity="critical",
                    message=f"Container '{c_name}' in {kind}/{name} is running in Privileged mode.",
                    resource_name=name,
                    resource_kind=kind,
                    file_path=fpath,
                    impact_description="Privileged containers have near-complete access to the host kernel and devices.",
                    risk_level="CRITICAL",
                )
            )

        # 2. Privilege Escalation
        if sc.get("allowPrivilegeEscalation") is not False:
            # Default is True in K8s, so we flag if not explicitly set to False
            findings.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    rule_id=Rules.ALLOW_PRIVILEGE_ESCALATION,
                    severity="high",
                    message=f"Container '{c_name}' in {kind}/{name} allows privilege escalation.",
                    resource_name=name,
                    resource_kind=kind,
                    file_path=fpath,
                    suggestion="Set 'allowPrivilegeEscalation: false'.",
                    risk_level="HIGH",
                )
            )

        # 3. Read Only Root Filesystem
        if sc.get("readOnlyRootFilesystem") is not True:
            findings.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    rule_id="rule/read-only-root-filesystem",
                    severity="warning",
                    message=f"Container '{c_name}' in {kind}/{name} does not have a read-only root filesystem.",
                    resource_name=name,
                    resource_kind=kind,
                    file_path=fpath,
                    suggestion="Set 'readOnlyRootFilesystem: true'.",
                    risk_level="MEDIUM",
                )
            )

        # 4. Capabilities
        caps = sc.get("capabilities") or {}
        add_caps = caps.get("add") or []
        if not isinstance(add_caps, list):
            add_caps = []

        intersect = set([c.upper() for c in add_caps]).intersection(self.DANGEROUS_CAPS)
        if intersect:
            findings.append(
                AnalysisResult(
                    analyzer_name=self.name,
                    rule_id=Rules.DANGEROUS_CAPABILITIES,
                    severity="critical",
                    message=f"Container '{c_name}' in {kind}/{name} uses dangerous capabilities: {', '.join(intersect)}.",
                    resource_name=name,
                    resource_kind=kind,
                    file_path=fpath,
                    impact_description="Dangerous capabilities allow for kernel manipulation, network sniffing, and filesystem bypass.",
                    risk_level="CRITICAL",
                )
            )

    def _audit_volumes(self, pod_spec: dict, kind: str, name: str, fpath: str, findings: List[AnalysisResult]):
        volumes = pod_spec.get("volumes") or []
        for vol in volumes:
            if not hasattr(vol, "get"):
                continue
            hp = vol.get("hostPath")
            if not hasattr(hp, "get"):
                continue

            path = hp.get("path", "")
            if any(path.startswith(s) for s in self.SENSITIVE_PATHS):
                findings.append(
                    AnalysisResult(
                        analyzer_name=self.name,
                        rule_id=Rules.UNSAFE_HOSTPATH,
                        severity="critical",
                        message=f"Pod {kind}/{name} mounts sensitive host path: {path}.",
                        resource_name=name,
                        resource_kind=kind,
                        file_path=fpath,
                        impact_description="Sensitive host paths allow containers to access or modify host-level configuration, secrets, or processes.",
                        risk_level="CRITICAL",
                    )
                )

    def _remediate(self, doc: dict) -> bool:
        """[S2: Apply] Hardens securityContext fields and host isolation."""
        modified = False
        pod_spec = find_pod_spec(doc)
        if not pod_spec:
            return False

        # 1. Pod Level Host Isolation
        for field in ["hostNetwork", "hostPID", "hostIPC"]:
            if pod_spec.get(field) is True:
                pod_spec[field] = False
                modified = True

        # 2. Pod Level SecurityContext
        sc_pod = pod_spec.get("securityContext")
        if sc_pod is None:
            pod_spec["securityContext"] = {"runAsNonRoot": True, "runAsUser": 1000}
            modified = True
        elif hasattr(sc_pod, "get"):
            if sc_pod.get("runAsNonRoot") is not True:
                sc_pod["runAsNonRoot"] = True
                modified = True
            if sc_pod.get("runAsUser") == 0:
                sc_pod["runAsUser"] = 1000
                modified = True

        # 3. Container Level Hardening
        for c in extract_containers(doc):
            if not hasattr(c, "get"):
                continue
            sc_c = c.get("securityContext")
            if sc_c is None:
                c["securityContext"] = {
                    "allowPrivilegeEscalation": False,
                    "runAsNonRoot": True,
                    "readOnlyRootFilesystem": True,
                    "privileged": False,
                    "capabilities": {"drop": ["ALL"]},
                }
                modified = True
            elif hasattr(sc_c, "get"):
                if sc_c.get("allowPrivilegeEscalation") is not False:
                    sc_c["allowPrivilegeEscalation"] = False
                    modified = True
                if sc_c.get("privileged") is True:
                    sc_c["privileged"] = False
                    modified = True
                if sc_c.get("readOnlyRootFilesystem") is not True:
                    sc_c["readOnlyRootFilesystem"] = True
                    modified = True

                # Drop all capabilities if not already doing so
                caps = sc_c.get("capabilities") or {}
                if "drop" not in caps or "ALL" not in [d.upper() for d in caps.get("drop", [])]:
                    sc_c["capabilities"] = caps
                    caps["drop"] = ["ALL"]
                    modified = True

        return modified
