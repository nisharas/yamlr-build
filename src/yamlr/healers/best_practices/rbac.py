#!/usr/bin/env python3
"""
Yamlr RBAC AUDITOR - Forensic Permission Analysis
-------------------------------------------------
Detects and remediates security risks in Kubernetes RBAC resources.

Why: Over-privileged RBAC roles (wildcards) and suspicious bindings 
     are a primary vector for cluster-wide escalation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from yamlr.analyzers.base import AnalysisResult
from yamlr.analyzers.rules import Rules

logger = logging.getLogger("yamlr.healers.best_practices.rbac")

class RBACAuditor:
    """
    Forensic auditor for Role, ClusterRole, and their Bindings.
    """

    SENSITIVE_RESOURCES = {"secrets", "configmaps", "pods/exec", "pods/attach", "pods/proxy", "nodes/proxy"}
    SENSITIVE_VERBS = {"*", "get", "list", "watch", "create", "update", "patch", "delete", "deletecollection", "impersonate"}

    def __init__(self):
        self.name = "RBACAuditor"

    def heal_doc(self, doc: Any, context: Any = None, harden: bool = False) -> bool:
        """
        Audits an RBAC document and attaches findings to the context.
        Returns True if auto-remediations are applied (S2: Apply).
        """
        if not hasattr(doc, "get"):
            return False

        kind = doc.get("kind", "")
        if kind not in ["Role", "ClusterRole", "RoleBinding", "ClusterRoleBinding"]:
            return False

        findings = []
        modified = False

        if kind in ["Role", "ClusterRole"]:
            modified = self._audit_role(doc, findings)
            if harden:
                modified = self._remediate_wildcards(doc) or modified
        elif kind in ["RoleBinding", "ClusterRoleBinding"]:
            modified = self._audit_binding(doc, findings)

        if findings and context and hasattr(context, "add_finding"):
            for f in findings:
                context.add_finding(f)

        return modified

    def _remediate_wildcards(self, doc: dict) -> bool:
        """
        [S2: Apply] Remediates RBAC wildcards by adding descriptive comments
        and converting risky verbs to read-only defaults where safe.
        """
        rules = doc.get("rules", [])
        if not isinstance(rules, list):
            return False

        modified = False
        for rule in rules:
            if not isinstance(rule, dict):
                continue

            verbs = rule.get("verbs", [])
            resources = rule.get("resources", [])
            
            # Use 'k8s.io/yamlr' annotation-like structure if we had a comment-preserving parser
            # But here we are working on the dict.
            
            if "*" in verbs:
                # Rule: Convert '*' to read-only set if hardening is requested.
                # This is a 'Safe-Fail' remediation.
                rule["verbs"] = ["get", "list", "watch"]
                logger.info(f"[RBAC] REMEDIATED: Replaced '*' verbs with safe read-only set in {doc.get('kind')} '{doc.get('metadata', {}).get('name')}'")
                modified = True

            if "*" in resources:
                # For resources, we don't know the intent, so we leave it but could add a marker.
                # In this implementation, we only remediate verbs for now as it's the safest 'S2' path.
                pass

        return modified

    def _audit_role(self, doc: dict, findings: List[AnalysisResult]) -> bool:
        rules = doc.get("rules", [])
        if not isinstance(rules, list):
            return False

        name = doc.get("metadata", {}).get("name", "unnamed")
        kind = doc.get("kind", "")
        fpath = doc.get("__file_path__", "unknown") if hasattr(doc, "get") else "unknown"
        for rule in rules:
            if not isinstance(rule, dict):
                continue

            verbs = rule.get("verbs", [])
            resources = rule.get("resources", [])
            api_groups = rule.get("apiGroups", [])
            
            logger.debug(f"[RBAC] Auditing rule for {kind}/{name}: verbs={verbs}, resources={resources}, apiGroups={api_groups}")

            # 1. Check for Wildcards (RBAC_WILDCARD)
            safe_verbs = verbs or []
            safe_resources = resources or []
            safe_groups = api_groups or []
            
            if "*" in safe_verbs or "*" in safe_resources or "*" in safe_groups:
                findings.append(AnalysisResult(
                    analyzer_name=self.name,
                    severity="error",
                    message=f"RBAC Wildcard detected in {kind} '{name}'. Over-privileged permissions found.",
                    resource_name=name,
                    resource_kind=kind,
                    rule_id=Rules.RBAC_WILDCARD,
                    file_path=fpath,
                    suggestion="Specify explicit verbs and resources instead of '*'.",
                    impact_description="Overly broad permissions (wildcards) allow for cluster-wide lateral movement.",
                    rationale="Least-privilege requires explicit sets of verbs and resources.",
                    risk_level="HIGH"
                ))

            # 2. Check for Privilege Escalation (RBAC_PRIVILEGE_ESCALATION)
            self._check_privilege_escalation(rule, name, kind, fpath, findings)

            # 3. Check for Sensitive Resource Access (RBAC_SENSITIVE_RESOURCE)
            intersect_res = [r for r in safe_resources if r in self.SENSITIVE_RESOURCES]
            has_sensitive_verb = any(v in self.SENSITIVE_VERBS for v in safe_verbs)
            
            if intersect_res and has_sensitive_verb:
                 findings.append(AnalysisResult(
                    analyzer_name=self.name,
                    severity="critical",
                    message=f"Sensitive access allowed in {kind} '{name}' to resources: {', '.join(intersect_res)}.",
                    resource_name=name,
                    resource_kind=kind,
                    rule_id=Rules.RBAC_SENSITIVE_RESOURCE,
                    file_path=fpath,
                    impact_description="Sensitive resources like 'secrets' or 'nodes/proxy' allow for immediate environment takeover.",
                    rationale="Restrict access to sensitive resources to specific service accounts only.",
                    risk_level="HIGH"
                ))

        return False

    def _audit_binding(self, doc: dict, findings: List[AnalysisResult]) -> bool:
        subjects = doc.get("subjects", [])
        if not isinstance(subjects, list):
            return False

        name = doc.get("metadata", {}).get("name", "unnamed")
        kind = doc.get("kind", "")
        fpath = doc.get("__file_path__", "unknown")

        SUSPICIOUS_GROUPS = {"system:authenticated", "system:unauthenticated"}

        for sub in subjects:
            if not isinstance(sub, dict):
                continue

            s_kind = sub.get("kind", "")
            s_name = sub.get("name", "")
            
            # Check for broad group bindings or default SAs (RBAC_SUSPICIOUS_BINDING)
            is_suspicious = (s_kind == "Group" and s_name in SUSPICIOUS_GROUPS) or \
                           (s_kind == "ServiceAccount" and s_name == "default")

            if is_suspicious:
                findings.append(AnalysisResult(
                    analyzer_name=self.name,
                    severity="critical",
                    message=f"Binding '{name}' targets broad system group or default service account: {s_name}.",
                    resource_name=name,
                    resource_kind=kind,
                    rule_id=Rules.RBAC_SUSPICIOUS_BINDING,
                    file_path=fpath,
                    impact_description="Binding sensitive roles to everyone or default account facilitates anonymous or low-privilege cluster takeover.",
                    rationale="Bind roles only to specific users, groups, or service accounts.",
                    risk_level="MEDIUM"
                ))

        return False

    def _check_privilege_escalation(self, rule: Dict[str, Any], r_name: str, r_kind: str, fpath: str, findings: List[AnalysisResult]):
        """Detects risky combinations of verbs and resources (Legacy Merge)."""
        resources = rule.get("resources") or []
        verbs = rule.get("verbs") or []
        
        safe_resources = resources if isinstance(resources, list) else []
        safe_verbs = verbs if isinstance(verbs, list) else []
        
        RISKY_ESCALATION_RESOURCES = {
            "roles", "clusterroles", "rolebindings", "clusterrolebindings"
        }
        RISKY_VERBS = {"bind", "impersonate", "escalate", "update", "patch", "create"}

        intersect_res = set([r.lower() for r in safe_resources if isinstance(r, str)]).intersection(RISKY_ESCALATION_RESOURCES)
        intersect_verbs = set([v.lower() for v in safe_verbs if isinstance(v, str)]).intersection(RISKY_VERBS)

        if intersect_res and intersect_verbs:
            findings.append(AnalysisResult(
                analyzer_name=self.name,
                rule_id=Rules.RBAC_PRIVILEGE_ESCALATION,
                severity="critical",
                message=f"RBAC {r_kind} '{r_name}' allows risky verbs ({', '.join(intersect_verbs)}) on RBAC management resources ({', '.join(intersect_res)}).",
                resource_name=r_name,
                resource_kind=r_kind,
                file_path=fpath,
                impact_description="A user with these permissions can escalate their own privileges or grant permissions to others.",
                rationale="Managing RBAC resources is a high-risk capability and must be extremely restricted.",
                risk_level="CRITICAL"
            ))
