#!/usr/bin/env python3
"""
Yamlr INGRESS AUDITOR - Forensic Security for Entrypoints
-------------------------------------------------------
Implements deep scanning and remediation for Ingress resources.

Why: Ingresses are the public gateway to the cluster; misconfigurations
     (missing TLS, snippet injections) are high-impact security risks.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from yamlr.analyzers.base import AnalysisResult
from yamlr.analyzers.rules import Rules
from yamlr.core.stages.boundaries import MutationScope

logger = logging.getLogger("yamlr.healers.ingress")

class IngressAuditor:
    """
    Forensic Auditor and Healer for Ingress Resources.
    """
    
    def __init__(self, default_ingress_class: str = "nginx"):
        self.default_ingress_class = default_ingress_class

    def scan_doc(self, doc: Any, fpath: str = "unknown") -> List[AnalysisResult]:
        """
        Scans an Ingress document for security risks.
        """
        if not isinstance(doc, dict) or doc.get("kind") != "Ingress":
            return []

        findings: List[AnalysisResult] = []
        name = doc.get("metadata", {}).get("name", "unnamed")
        spec = doc.get("spec", {})
        annotations = doc.get("metadata", {}).get("annotations", {})

        # 1. Ingress Class Audit
        self._audit_ingress_class(spec, annotations, name, fpath, findings)

        # 2. TLS Enforcement Audit
        self._audit_tls(spec, name, fpath, findings)

        # 3. Annotation Safety Audit (Snippet Injection)
        self._audit_annotations(annotations, name, fpath, findings)

        # 4. Host Security (Wildcards)
        self._audit_hosts(spec, name, fpath, findings)

        return findings

    def heal_doc(self, doc: Any, context: Any = None, harden: bool = False) -> bool:
        """
        Audits and remediates Ingress security risks.
        """
        if not isinstance(doc, dict) or doc.get("kind") != "Ingress":
            return False

        fpath = doc.get("__file_path__", "unknown")
        findings = self.scan_doc(doc, fpath=fpath)

        modified = False
        if harden:
            modified = self._remediate(doc, context)

        if findings and context and hasattr(context, "add_finding"):
            for f in findings:
                context.add_finding(f)

        return modified

    def _audit_ingress_class(self, spec: Dict[str, Any], annotations: Dict[str, Any], name: str, fpath: str, findings: List[AnalysisResult]):
        """Detects missing IngressClass or legacy annotations."""
        has_class = spec.get("ingressClassName") or annotations.get("kubernetes.io/ingress.class")
        if not has_class:
            findings.append(AnalysisResult(
                analyzer_name="ingress-auditor",
                rule_id=Rules.INGRESS_CLASS_MISSING,
                severity="warning",
                message=f"Ingress '{name}' is missing an explicit ingressClassName.",
                risk_level="MEDIUM",
                resource_name=name,
                resource_kind="Ingress",
                file_path=fpath,
                fix_available=True,
                fix_id="enforce_ingress_class"
            ))

    def _audit_tls(self, spec: Dict[str, Any], name: str, fpath: str, findings: List[AnalysisResult]):
        """Detects missing TLS configuration."""
        rules = spec.get("rules", [])
        tls = spec.get("tls", [])
        
        # If there are rules but no TLS, it's a security risk for production
        if rules and not tls:
            findings.append(AnalysisResult(
                analyzer_name="ingress-auditor",
                rule_id=Rules.INGRESS_TLS_MISSING,
                severity="high",
                message=f"Ingress '{name}' serves traffic over HTTP without TLS configuration.",
                risk_level="HIGH",
                resource_name=name,
                resource_kind="Ingress",
                file_path=fpath,
                fix_available=True,
                fix_id="inject_tls_stub"
            ))

    def _audit_annotations(self, annotations: Dict[str, Any], name: str, fpath: str, findings: List[AnalysisResult]):
        """Detects dangerous snippet injections in annotations."""
        dangerous_keys = [
            "nginx.ingress.kubernetes.io/configuration-snippet",
            "nginx.ingress.kubernetes.io/server-snippet",
            "nginx.org/server-snippets",
            "nginx.org/location-snippets"
        ]
        for key in dangerous_keys:
            if key in annotations:
                findings.append(AnalysisResult(
                    analyzer_name="ingress-auditor",
                    rule_id=Rules.INGRESS_UNSAFE_ANNOTATION,
                    severity="error",
                    message=f"Ingress '{name}' uses unsafe snippet annotation '{key}'.",
                    risk_level="CRITICAL",
                    resource_name=name,
                    resource_kind="Ingress",
                    file_path=fpath,
                    fix_available=False
                ))

    def _audit_hosts(self, spec: Dict[str, Any], name: str, fpath: str, findings: List[AnalysisResult]):
        """Detects wildcard or missing hosts."""
        rules = spec.get("rules", [])
        for rule in rules:
            if not rule.get("host"):
                findings.append(AnalysisResult(
                    analyzer_name="ingress-auditor",
                    rule_id=Rules.INGRESS_WILDCARD_HOST,
                    severity="warning",
                    message=f"Ingress '{name}' rule is missing a host (wildcard).",
                    risk_level="MEDIUM",
                    resource_name=name,
                    resource_kind="Ingress",
                    file_path=fpath,
                    fix_available=True,
                    fix_id="fix_ingress_host"
                ))

    def _remediate(self, doc: Dict[str, Any], context: Any) -> bool:
        """Applies S2: Apply fixes to the Ingress document."""
        modified = False
        spec = doc.setdefault("spec", {})
        metadata = doc.setdefault("metadata", {})
        annotations = metadata.setdefault("annotations", {})
        
        # 1. Inject IngressClass
        if not spec.get("ingressClassName") and not annotations.get("kubernetes.io/ingress.class"):
            spec["ingressClassName"] = self.default_ingress_class
            modified = True
            self._log_remediation(context, "spec.ingressClassName", f"Injected default IngressClass '{self.default_ingress_class}'")

        # 2. Fix Missing Hosts
        rules = spec.get("rules", [])
        for rule in rules:
            if not rule.get("host"):
                rule["host"] = "remediated.local"
                modified = True
                self._log_remediation(context, "spec.rules[].host", "Fixed missing Ingress host")

        # 3. Inject TLS Stub (if missing and rules exist)
        if rules and not spec.get("tls"):
            unique_hosts = list(set(r.get("host") for r in rules if r.get("host")))
            if unique_hosts:
                spec["tls"] = [{"hosts": unique_hosts, "secretName": f"{doc['metadata']['name']}-tls"}]
                modified = True
                self._log_remediation(context, "spec.tls", "Injected TLS configuration stub")

        return modified

    def _log_remediation(self, context: Any, target: str, description: str):
        """Helper to log remediation actions to the context."""
        if context and hasattr(context, "prescribe"):
            from yamlr.models import HealAction
            context.prescribe(HealAction(
                stage="IngressHardening",
                action_type="harden",
                target=target,
                description=description,
                rationale="Ingress resources must follow security best practices to prevent traffic exposure and class ambiguity.",
                suggestion="Explicitly define ingressClassName and TLS for all production ingresses.",
                severity="info",
                rule_id="rule/ingress-hardened",
                scope=MutationScope.STRUCTURAL
            ))
