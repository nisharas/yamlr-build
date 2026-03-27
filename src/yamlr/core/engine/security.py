"""
Unified Hardening Engine for Yamlr.
-----------------------------------
Centralizes security validation, PSS enforcement, and hostPath auditing.

### 🧩 Architectural Decision Records (Micro-ADR)

1. **2026-03-24: Centralized Penalty Map**
   - **Context**: Scoring logic was duplicated across analyzers.
   - **Decision**: Define a single `PENALTY_MAP` and `RULE_FIX_MAP` in `HardeningEngine`.
   - **Consequence**: Guaranteed consistency between "Scan Report" and "Heal Context".

2. **2026-03-25: hostPath Resolution Safety**
   - **Context**: `hostPath` validation can be bypassed by symlinks.
   - **Decision**: Enforce `.resolve()` before checking against `allowed_roots`.
   - **Consequence**: Prevents path traversal vulnerabilities via K8s volumes.
"""
from __future__ import annotations
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from yamlr.analyzers.base import AnalysisResult
from yamlr.core.k8s_utils import find_pod_spec
from yamlr.analyzers.rules import Rules
from yamlr.healers.best_practices.privilege_escalation import PrivilegeEscalationAuditor

logger = logging.getLogger("yamlr.engine.hardening")

__all__ = ["HardeningEngine"]

class HardeningEngine:
    """
    Single Source of Truth for Security Hardening and Validations.
    """
    
    # --- Rule ID Constants (Delegated to yamlr.analyzers.rules) ---
    RULE_UNSAFE_HOSTPATH = Rules.UNSAFE_HOSTPATH
    RULE_HOST_NETWORK = Rules.HOST_NETWORK
    RULE_HOST_PID = Rules.HOST_PID
    RULE_HOST_IPC = Rules.HOST_IPC
    RULE_RUN_AS_NON_ROOT = Rules.RUN_AS_ROOT
    RULE_PRIVILEGED = Rules.PRIVILEGED_CONTAINER
    RULE_PRIVILEGE_ESCALATION = Rules.ALLOW_PRIVILEGE_ESCALATION
    RULE_NO_LATEST_TAG = Rules.IMAGE_TAG_CHECK
    RULE_RESOURCE_LIMITS = Rules.RESOURCE_LIMITS
    RULE_RESOURCE_REQUESTS = Rules.RESOURCE_REQUESTS
    RULE_SCHEMA_VALIDATION = Rules.SCHEMA_MISMATCH
    RULE_SCHEMA_API = "schema/invalid-api-version"

    # --- Penalty Map (Sovereign Scoring) ---
    PENALTY_MAP: Dict[str, int] = {
        RULE_UNSAFE_HOSTPATH: 15,
        RULE_HOST_NETWORK: 15,
        RULE_HOST_PID: 15,
        RULE_HOST_IPC: 15,
        RULE_PRIVILEGED: 15,
        RULE_PRIVILEGE_ESCALATION: 10,
        RULE_RUN_AS_NON_ROOT: 10,
        RULE_NO_LATEST_TAG: 5,
        RULE_RESOURCE_LIMITS: 5,
        RULE_RESOURCE_REQUESTS: 2,
        RULE_SCHEMA_VALIDATION: 5,
        RULE_SCHEMA_API: 5,
        Rules.DANGEROUS_CAPABILITIES: 15,
        Rules.SENSITIVE_VOLUME_MOUNT: 15
    }

    # --- Remediation Fix Map (Audit v30 Finding 30.1) ---
    # Maps rule_ids to RemediationRegistry fix_ids for auto-healing.
    RULE_FIX_MAP: Dict[str, Optional[str]] = {
        RULE_RUN_AS_NON_ROOT: "enforce_non_root",
        RULE_PRIVILEGED: "disallow_privileged",
        RULE_PRIVILEGE_ESCALATION: "enforce_non_root",
        RULE_UNSAFE_HOSTPATH: None,  # No safe auto-fix; report only
        RULE_HOST_NETWORK: None,
        RULE_HOST_PID: None,
        RULE_HOST_IPC: None,
    }

    # Security Standards (Shared with Healers)
    SECURITY_STANDARDS = {
        "runAsNonRoot": True,
        "runAsUser": 1000,
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "privileged": False,
        "capabilities": {
            "drop": ["ALL"]
        }
    }

    
    def __init__(self, allowed_host_paths: Optional[List[str]] = None):
        self.allowed_host_paths = allowed_host_paths or ["/var/log", tempfile.gettempdir()]
        self.allowed_roots = [Path(a).resolve() for a in self.allowed_host_paths]
        self.auditor = PrivilegeEscalationAuditor()

    def apply_hardening_to_pod_spec(self, pod_spec: Dict[str, Any]) -> bool:
        """DELEGATED to PrivilegeEscalationAuditor for forensic consistency."""
        # Wrap in a minimal doc for the auditor
        doc = {"kind": "Pod", "spec": pod_spec}
        return self.auditor._remediate(doc)

    def apply_hardening_to_container(self, container: Dict[str, Any]) -> bool:
        """DELEGATED to PrivilegeEscalationAuditor for forensic consistency."""
        # Wrap in a minimal doc for the auditor
        doc = {
            "kind": "Pod", 
            "spec": {"containers": [container]}
        }
        return self.auditor._remediate(doc)

    def scan_manifest(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings = []
        kind = doc.get("kind", "unknown")
        name = doc.get("metadata", {}).get("name", "unknown")
        
        # 1. Forensic Audit (Delegated)
        results = self.auditor.scan_doc(doc)
        for r in results:
            findings.append({
                "rule_id": r.rule_id,
                "severity": r.severity,
                "message": r.message,
                "risk_level": r.risk_level
            })

        # 2. hostPath Volume Audit (Native to Engine)
        pod_spec = find_pod_spec(doc)
        if pod_spec:
            findings.extend(self._audit_hostpaths(pod_spec, name, kind))

        return findings

    def _audit_hostpaths(self, pod_spec: Dict[str, Any], name: str, kind: str) -> List[Dict[str, Any]]:
        findings = []
        volumes = pod_spec.get("volumes") or []
        logger.debug("Probing %d volumes for hostPath: %s", len(volumes), volumes)
        for vol in volumes:
            hp = vol.get("hostPath")
            if isinstance(hp, dict) and hp.get("path"):
                path_str = hp["path"]
                logger.debug("Found hostPath: %s", path_str)
                try:
                    resolved = Path(path_str).resolve()
                    # [ROUND-11] Portable relative check for maximum M&A valuation (Python 3.9+ fallback)
                    is_allowed = False
                    for root in self.allowed_roots:
                        try:
                            resolved.relative_to(root)
                            is_allowed = True
                            break
                        except ValueError:
                            continue
                            
                    logger.debug("Resolved: %s, Allowed: %s", resolved, is_allowed)
                    if not is_allowed:
                        findings.append({
                            "rule_id": self.RULE_UNSAFE_HOSTPATH,
                            "severity": "high",
                            "message": f"Volume '{vol.get('name')}' in {kind}/{name} uses unsafe hostPath '{path_str}'",
                            "risk_level": "CRITICAL"
                        })
                except Exception as e:
                    logger.debug("Path resolution error: %s", e)
                    findings.append({
                        "rule_id": self.RULE_UNSAFE_HOSTPATH,
                        "severity": "high",
                        "message": f"Failed to resolve hostPath '{path_str}' in {kind}/{name}",
                        "risk_level": "HIGH"
                    })
        return findings

    def scan_docs(self, docs: List[Any]) -> List[Dict[str, Any]]:
        """
        Scans a list of parsed documents for security findings.
        Why: Eliminates the need to re-parse YAML if we already have the dicts.
        """
        all_findings = []
        logger.debug("HardeningEngine scanning %d docs", len(docs))
        for doc_node in docs:
            # [FIX] Explicitly handle YamlrNode (Shadow/Pro) vs raw dict
            if hasattr(doc_node, "to_dict"):
                doc = doc_node.to_dict()
            elif hasattr(doc_node, "is_map") and doc_node.is_map:
                 # It might be a YamlrNode but without to_dict if it's a proxy
                 doc = {k: doc_node[k] for k in doc_node.keys()}
            else:
                doc = doc_node
                
            if not isinstance(doc, dict): 
                logger.debug("Skipping non-dict doc: %s", type(doc))
                continue
            
            logger.debug("Scanning doc with keys: %s", list(doc.keys()))
            all_findings.extend(self.scan_manifest(doc))
        return all_findings



    def apply_penalties_to_context(self, context: Any) -> int:
        """
        Calculates and applies total penalty from all findings in context.
        Why: Ensures trust_score is affected by all identified violations 
             (schema, security, best practices) in a single pass.
             Now also sets fix_id/fix_available to close the remediation loop.
        """
        # 1. First, run our own security-specific scans
        security_findings = self.scan_docs(context.docs)
        
        # 2. Add our findings to context (deduped), with fix_id for auto-healing
        for f_data in security_findings:
            rule_id = f_data["rule_id"]
            is_duplicate = any(getattr(x, "rule_id", None) == rule_id and getattr(x, "message", None) == f_data["message"] for x in context.findings)
            if not is_duplicate:
                fix_id = self.RULE_FIX_MAP.get(rule_id)
                context.findings.append(AnalysisResult(
                    analyzer_name="hardening-engine",
                    rule_id=rule_id,
                    severity=f_data["severity"],
                    message=f_data["message"],
                    risk_level=f_data.get("risk_level", "HIGH"),
                    resource_name=(context.docs[0].get("metadata", {}).get("name") if context.docs else "unknown"),
                    resource_kind=(context.docs[0].get("kind") if context.docs else "unknown"),
                    file_path=context.file_path or "unknown",
                    fix_available=fix_id is not None,
                    fix_id=fix_id,
                ))


        # 3. Holistic Penalty Calculation
        penalty = self._calculate_total_penalty(context)
        return penalty

    def _calculate_total_penalty(self, context: Any) -> int:
        """Helper to sum up penalties and update trust score."""
        penalty = 0
        for f in context.findings:
            rule_id = getattr(f, "rule_id", "unknown")
            p_val = self.PENALTY_MAP.get(rule_id, 0)
            if p_val > 0:
                penalty += p_val
                self._log_security_warning(context, f.message)

        current_trust = getattr(context, "trust_score", 100.0)
        context.trust_score = max(0.0, current_trust - penalty)
        logger.debug("Holistic penalty -%d. New trust_score: %s", penalty, context.trust_score)
        return penalty

    def _log_security_warning(self, context: Any, message: str):
        """Helper to add warning to context audit log."""
        if f"  → {message}" not in context.audit_log:
            if "⚠️ Security/Validation Warnings identified:" not in context.audit_log:
                context.audit_log.append("⚠️ Security/Validation Warnings identified:")
            context.audit_log.append(f"  → {message}")
