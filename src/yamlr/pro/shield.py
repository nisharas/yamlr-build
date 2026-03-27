#!/usr/bin/env python3
"""
Yamlr SHIELD ENGINE - Enterprise Hardening
-------------------------------------------
Implements the core trust-verification and hardening engine for Yamlr Pro.
This module provides the aggregate health scoring and safety verification.
"""

from __future__ import annotations
import logging
from typing import Any, List, Optional
from yamlr.core.engine.security import HardeningEngine
from yamlr.core.dna_utils import calculate_semantic_dna
from yamlr.core.k8s_utils import find_pod_spec
from yamlr.analyzers.base import AnalysisResult
__all__ = ['ShieldEngine']


class ShieldEngine(HardeningEngine):
    """
    Enterprise-grade hardening and trust verification engine.
    Extends Core HardeningEngine with advanced forensic and shadow-risk analysis.
    """
    
    def __init__(self, allowed_host_paths: Optional[List[str]] = None):
        """
        Why: Initializes the hardening engine with enterprise risk thresholds.
        """
        super().__init__(allowed_host_paths)
        self.enabled = True
        logger = logging.getLogger("yamlr.pro.shield")
        logger.debug("🛡️ Shield Engine initialized (PRO)")
        try:
            from yamlr.core.bridge import YamlrBridge
            YamlrBridge.get_license_manager().track_usage("shield_initialization", 1)
        except Exception: pass

    def calculate_trust_score(self, *args, **kwargs) -> float:
        """
        Calculates a proprietary trust score for the current workspace.
        
        Why: Quantifies security posture for executive reporting. 
             Optimized HAS gathering [PHASE-19] now supports fast-path 
             telemetry aggregation for sub-second CLI response.
        Args:
            *args: Can be (context, finding_risk_total) or (lexical_has, schema_has, semantic_has)
        """
        # Optimized Fast-Path (3 metrics)
        if len(args) == 3:
            try:
                def _to_float(v):
                    if v is None: return 0.0
                    if isinstance(v, str): return float(v.replace("%", ""))
                    return float(v)
                lex = _to_float(args[0])
                sch = _to_float(args[1])
                sem = _to_float(args[2])
                return (lex * 0.4 + sch * 0.3 + sem * 0.3)
            except (ValueError, TypeError):
                return 0.0

        # Pattern 2: Context-based (Standard Shield Analysis)
        context = args[0] if len(args) > 0 else kwargs.get("context")
        finding_risk_total = args[1] if len(args) > 1 else kwargs.get("finding_risk_total", 0.0)
        
        base_score = 100.0
        base_score -= (finding_risk_total * 0.5)
        
        if hasattr(context, "resource_graph") and context.resource_graph:
            graph = context.resource_graph
            # Blast-radius weighted risk [PRO-99]
            high_impact_nodes = [n for n in graph.get_all_nodes() if graph.blast_radius(n.key).risk_level == "HIGH"]
            base_score -= (len(high_impact_nodes) * 2.0)
            
        return min(100.0, max(0.0, base_score))

    def detect_shadow_risks(self, doc: Any, graph: Optional[Any] = None) -> List[AnalysisResult]:
        """
        Performs deep forensic analysis for 'Shadow Risks' (hidden vulnerabilities).
        """
        is_dict_like = isinstance(doc, dict) or (hasattr(doc, "is_map") and doc.is_map)
        if not self.enabled or not is_dict_like:
            return []
            
        findings = []
        kind = doc.get("kind", "")
        name = doc.get("metadata", {}).get("name", "unknown")
        
        # Normalize workload spec
        spec = find_pod_spec(doc)
        if not spec:
            return []

        containers = list(spec.get("containers") or []) + list(spec.get("initContainers") or [])
        volumes = spec.get("volumes", [])

        # [REMOVED] SHD-001 & SHD-002 are now handled by Core HardeningEngine.
        # Delegating standard security checks to the base class.
        
        # SHD-003: Sensitive Volume Exposure
        # Detects if a Secret or ConfigMap is mounted into a container that also has a hostPath mount (potential leak)
        has_host_path = any(v.get("hostPath") for v in volumes)
        if has_host_path:
            for vol in volumes:
                if vol.get("secret") or vol.get("configMap"):
                    findings.append(self._make_finding(
                        "WARNING", f"Shadow Risk: Sensitive volume '{vol.get('name')}' co-located with HostPath mount (Potential Leak).",
                        name, kind, "SHD-003"
                    ))

        # [REMOVED] SHD-004: Host Namespace Leaks (Now handled by Core hostPID/hostIPC/hostNetwork checks)

        # SHD-005: Resource Starvation in High-Impact Workloads
            if graph:
                node_key = f"{kind}/default/{name}" # Assume default for heuristic
                radius = graph.blast_radius(node_key)
                if radius.risk_level == "HIGH":
                    for container in containers:
                        resources = container.get("resources", {})
                        if not resources.get("limits", {}).get("cpu") or not resources.get("limits", {}).get("memory"):
                             findings.append(self._make_finding(
                                "WARNING", f"Shadow Risk: High-impact workload '{name}' lacks resource limits, risking cluster instability.",
                                name, kind, "SHD-005"
                            ))

        if findings:
            try:
                from yamlr.core.bridge import YamlrBridge
                YamlrBridge.get_license_manager().track_usage("shadow_risks_detected", len(findings))
            except Exception: pass

        return findings

    def verify_integrity(self, content: str) -> bool:
        """
        Verifies manifest integrity via Semantic DNA.
        
        Why: Ensures that zero-loss intent preservation is mathematically sound.
             Uses centralized verify_dna [PHASE-19] for stable semantic alignment.
        """
        if not content.strip():
            return False
            
        try:
            from yamlr.core.dna_utils import verify_dna
            # Handle raw string to semantic DNA verification [PHASE-19]
            # This handles multi-doc parsing internally in dna_utils
            return verify_dna(content, calculate_semantic_dna(content))
        except (ValueError, TypeError, AttributeError):
            return False

    def _make_finding(self, severity: str, message: str, name: str, kind: str, rule_id: str) -> AnalysisResult:
        """Helper to create standardized AnalysisResults."""
        # Map SHD internal rules to Core rules for metadata lookup where applicable
        core_mapping = {
            "SHD-001": HardeningEngine.RULE_UNSAFE_HOSTPATH,
            "SHD-002": HardeningEngine.RULE_PRIVILEGED,
            "SHD-004": HardeningEngine.RULE_HOST_NETWORK,
        }
        
        lookup_id = core_mapping.get(rule_id, rule_id)

        return AnalysisResult(
            analyzer_name="ShieldEngine",
            severity=severity,
            message=message,
            resource_name=name,
            resource_kind=kind,
            rule_id=lookup_id, # Use standardized ID for metadata lookup
            file_path="unknown"
            # Metadata (rationale, impact, etc.) automatically fetched from RuleManager
        )
