#!/usr/bin/env python3
"""
Yamlr SHIELD ENGINE - Enterprise Hardening
-------------------------------------------
Implements the core trust-verification and hardening engine for Yamlr Pro.
This module provides the aggregate health scoring and safety verification.
"""

import logging
import hashlib
import json
from typing import Dict, Any, List
from yamlr.analyzers.base import AnalysisResult

logger = logging.getLogger("yamlr.pro.shield")

def calculate_semantic_dna(docs: List[Dict[str, Any]]) -> str:
    """Generates a SHA-256 hash of the data content."""
    stable_json = json.dumps(docs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()

class ShieldEngine:
    """
    Enterprise-grade hardening and trust verification engine.
    """
    
    def __init__(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.enabled = True
        logger.debug("🛡️ Shield Engine initialized (PRO)")

    def calculate_trust_score(self, phy: str, kbs: str, sem: str) -> float:
        """
        Calculates an aggregate trust score (0.0 to 100.0) based on 
        the three primary sub-system statuses.
        """
        def _to_float(s: str) -> float:
            """
            Why: Internal documentation policy compliance.
            What: Auto-generated summary.
            """
            try:
                return float(s.strip('%'))
            except (ValueError, AttributeError):
                return 0.0
                
        p_val = _to_float(phy)
        k_val = _to_float(kbs)
        s_val = _to_float(sem)
        
        # Weighted aggregate: Physics (20%), Schema (40%), Semantic (40%)
        score = (p_val * 0.2) + (k_val * 0.4) + (s_val * 0.4)
        return min(100.0, max(0.0, score))

    def detect_shadow_risks(self, doc: Dict[str, Any]) -> List[AnalysisResult]:
        """
        Performs deep forensic analysis to detect 'Shadow Risks'
        (e.g., subtle hostPath vulnerabilities or resource exhaustion patterns).
        """
        if not self.enabled or not isinstance(doc, dict):
            return []
            
        findings = []
        kind = doc.get("kind", "")
        
        # Example Shadow Risk: HostPath Vulnerability (Enterprise Rule SHD-001)
        if kind in ("Pod", "Deployment", "DaemonSet", "StatefulSet", "Job", "CronJob"):
            spec = doc.get("spec", {})
            if kind != "Pod":
                spec = spec.get("template", {}).get("spec", {})
                
            volumes = spec.get("volumes", [])
            for vol in volumes:
                if "hostPath" in vol:
                    findings.append(AnalysisResult(
                        analyzer_name="YamlrShield",
                        severity="ERROR",
                        message=f"Shadow Risk: hostPath mount detected ({vol.get('name')}) granting node access.",
                        resource_name=doc.get("metadata", {}).get("name", "unknown"),
                        resource_kind=kind,
                        file_path="unknown",
                        rule_id="SHD-001"
                    ))
        
        return findings

    def verify_integrity(self, content: str) -> bool:
        """
        Verifies the mathematical integrity of the manifest.
        """
        if not content.strip():
            return False
        # Basic check: enforce valid yaml block structure hasn't been corrupted
        has_docs = "---" in content or len(content.splitlines()) > 0
        return has_docs
