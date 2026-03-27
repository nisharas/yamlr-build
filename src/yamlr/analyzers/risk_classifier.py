#!/usr/bin/env python3
"""
Yamlr RISK CLASSIFIER
-----------------------
Heuristic-based risk classification engine for Kubernetes configuration findings.

Why: Transforms raw findings into safety assessments with impact, scope,
     and risk level. Enterprise buyers prefer explainable heuristics over
     ML black boxes — "We use 14 hardcoded rules across 15 categories"
     is an advantage for auditability and determinism.

Architecture:
    - Consumes AnalysisResult + ResourceGraph to produce RiskAssessment.
    - Pure logic (no I/O, no side-effects). Transformation layer only.
    - Heuristics are explicit and documented for M&A due diligence.

Gate Compliance:
    - Trust: Read-only analysis (no changes to findings or graph).
    - Determinism: Same finding + same graph = same risk level.
    - Speed: O(1) per finding (graph traversal already computed).

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-28
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from yamlr.analyzers.base import AnalysisResult
from yamlr.core.resource_graph import ResourceGraph

logger = logging.getLogger("yamlr.risk_classifier")


# =====================================================================
# RISK CATEGORIES
# =====================================================================

# Canonical risk categories for safety-oriented output framing.
# These map to the "Category" line in CLI safety reports.
# 15 categories covering all known K8s failure modes.
CATEGORY_TRAFFIC = "Traffic Routing Failure"
CATEGORY_DATA = "Data Dependency Risk"
CATEGORY_RESOURCE = "Resource Exhaustion Risk"
CATEGORY_AVAILABILITY = "Availability Risk"
CATEGORY_SECURITY = "Security Posture Weakness"
CATEGORY_RBAC = "Authorization Failure Risk"
CATEGORY_VERSION = "Version Compatibility Risk"
CATEGORY_ORPHAN = "Namespace Clutter"
CATEGORY_HYGIENE = "Configuration Hygiene"
# Phase 2 categories (EPIC-23)
CATEGORY_SCHEDULING = "Scheduling Failure Risk"
CATEGORY_NETWORK_ISOLATION = "Network Isolation Risk"
CATEGORY_DISRUPTION = "Disruption Tolerance Risk"
CATEGORY_IMAGE = "Image Pull Failure Risk"
CATEGORY_CRD = "CRD Dependency Risk"
CATEGORY_REPLICA = "Replica Configuration Risk"
__all__ = ['RiskAssessment', 'RiskClassifier']



@dataclass
class RiskAssessment:
    """Result of risk classification for a single finding.

    Why: Structured risk data enables risk-oriented CLI output
         and SARIF enrichment for GitHub Security integration.
    """

    risk_level: str = "UNKNOWN"
    impact_description: str = ""
    scope_count: int = 0
    propagation_depth: int = 0
    affected_resources: List[str] = field(default_factory=list)
    category: str = "Uncategorized"


class RiskClassifier:
    """Heuristic risk scorer for Kubernetes configuration findings.

    Why: The classifier is the bridge between raw detection and
         safety-oriented presentation. It answers: "How dangerous
         is this issue, and what else does it affect?"

    Design:
        - No ML. No fancy math. Explainable heuristics only.
        - Each rule is a simple function that checks conditions.
        - Rules are applied in priority order (first match wins).
        - Enterprise buyers can audit every classification decision.

    Usage:
        classifier = RiskClassifier()
        assessment = classifier.classify(finding, graph)
        finding.risk_level = assessment.risk_level
    """

    def classify(
        self,
        finding: AnalysisResult,
        graph: Optional[ResourceGraph] = None,
    ) -> RiskAssessment:
        """Classify a finding into a risk assessment.

        Why: Single entry-point for risk classification. Returns a
             RiskAssessment that can be applied to the finding's
             safety-oriented fields.

        Args:
            finding: The raw analysis result to classify.
            graph: Optional resource graph for blast-radius enrichment.

        Returns:
            RiskAssessment with risk_level, impact, scope, and category.
        """
        assessment = RiskAssessment()

        # Step 1: Determine category from finding attributes
        assessment.category = self._categorize(finding)

        # Step 2: Calculate scope from graph (if available)
        if graph:
            node_key = self._build_node_key(finding)
            if node_key:
                radius = graph.blast_radius(node_key)
                assessment.scope_count = len(radius.affected_nodes)
                assessment.propagation_depth = radius.depth
                assessment.affected_resources = [
                    n.key for n in radius.affected_nodes
                ]

        # Step 3: Apply heuristic rules (priority order)
        assessment.risk_level = self._score_risk(finding, assessment)
        assessment.impact_description = self._describe_impact(
            finding, assessment
        )

        return assessment

    def enrich_finding(
        self,
        finding: AnalysisResult,
        graph: Optional[ResourceGraph] = None,
    ) -> AnalysisResult:
        """Classify and apply risk data directly to a finding.

        Why: Convenience method for pipeline integration. Modifies
             the finding in-place with safety-oriented fields.

        Args:
            finding: The finding to enrich.
            graph: Optional resource graph for blast-radius enrichment.

        Returns:
            The same finding, enriched with risk data.
        """
        assessment = self.classify(finding, graph)
        finding.risk_level = assessment.risk_level
        finding.impact_description = assessment.impact_description
        finding.scope_count = assessment.scope_count
        finding.propagation_depth = assessment.propagation_depth
        finding.affected_resources = assessment.affected_resources
        finding.risk_category = assessment.category
        return finding

    # =====================================================================
    # HEURISTIC RULES (Private)
    # =====================================================================

    def _categorize(self, finding: AnalysisResult) -> str:
        """Determine the risk category from finding attributes via mapping."""
        analyzer = (finding.analyzer_name or "").lower()
        rule_id = (finding.rule_id or "").lower()
        kind = (finding.resource_kind or "").lower()
        message = (finding.message or "").lower()

        # 1. Exact Kind Matches
        kind_map = {
            "networkpolicy": CATEGORY_NETWORK_ISOLATION,
            "poddisruptionbudget": CATEGORY_DISRUPTION,
            "priorityclass": CATEGORY_SCHEDULING,
            "runtimeclass": CATEGORY_SCHEDULING,
            "customresourcedefinition": CATEGORY_CRD,
        }
        if kind in kind_map:
            return kind_map[kind]

        # 2. Rule ID Keyword Matches (Priority Order)
        kw_mappings = [
            (["networkpolicy", "network_policy"], CATEGORY_NETWORK_ISOLATION),
            (["pdb", "disruption"], CATEGORY_DISRUPTION),
            (["image", "pull", "registry", "tag"], CATEGORY_IMAGE),
            (["ghost", "selector", "port", "ingress", "gateway", "httproute"], CATEGORY_TRAFFIC),
            (["orphan"], CATEGORY_ORPHAN),
            (["replica", "replicas", "scale"], CATEGORY_REPLICA),
            (["priorityclass", "runtimeclass", "toleration", "nodeselector", "affinity"], CATEGORY_SCHEDULING),
            (["crd", "customresource"], CATEGORY_CRD),
            (["configmap", "secret", "pvc", "volume"], CATEGORY_DATA),
            (["limit", "resource", "cpu", "memory"], CATEGORY_RESOURCE),
            (["probe", "liveness", "readiness", "hpa"], CATEGORY_AVAILABILITY),
            (["security", "privilege", "capabilities", "pss", "shd"], CATEGORY_SECURITY),
            (["rbac", "role", "binding", "serviceaccount"], CATEGORY_RBAC),
            (["deprecated", "migration", "version", "api"], CATEGORY_VERSION),
        ]
        
        for kws, cat in kw_mappings:
            if any(kw in rule_id for kw in kws):
                return cat

        # 3. Message/Analyzer Backups
        if "deprecat" in message: return CATEGORY_VERSION
        if "harden" in analyzer or "security" in analyzer: return CATEGORY_SECURITY
        if "orphan" in message: return CATEGORY_ORPHAN
        
        return CATEGORY_HYGIENE

    def _score_risk(self, finding: AnalysisResult, assessment: RiskAssessment) -> str:
        """Heuristic risk level determination with simplified logic."""
        severity = (finding.severity or "").upper()
        category = assessment.category
        scope = assessment.scope_count
        kind = (finding.resource_kind or "").lower()

        # HIGH Risk Conditions
        is_high = any([
            scope >= 3,
            category == CATEGORY_NETWORK_ISOLATION,
            category == CATEGORY_IMAGE,
            category == CATEGORY_TRAFFIC and scope > 0,
            category == CATEGORY_TRAFFIC and (kind in ("ingress", "httproute", "gateway")),
            category == CATEGORY_DATA and scope > 0,
            category == CATEGORY_SECURITY and severity in ("ERROR", "CRITICAL"),
            finding.risk_level == "HIGH"
        ])
        if is_high: return "HIGH"

        # MEDIUM Risk Conditions
        medium_cats = {CATEGORY_RESOURCE, CATEGORY_AVAILABILITY, CATEGORY_VERSION, 
                       CATEGORY_RBAC, CATEGORY_SCHEDULING, CATEGORY_CRD, CATEGORY_REPLICA}
        if scope >= 1 or category in medium_cats:
            return "MEDIUM"

        return "LOW"

    def _describe_impact(
        self, finding: AnalysisResult, assessment: RiskAssessment
    ) -> str:
        """Generate a human-readable impact description.

        Why: Impact descriptions transform "Missing field" into
             "Service will not route traffic." This is the identity shift.
        
        Note: [Phase 9] Prioritize high-fidelity context from Rule DB if available.

        Strategy: Category-driven templates with scope injection.
        """
        # [PHASE-9-FIX] Prioritize explicit high-fidelity impact from Rule DB
        if finding.impact_description and finding.impact_description not in (None, "None", ""):
            return finding.impact_description

        scope = assessment.scope_count
        category = assessment.category
        kind = finding.resource_kind or "resource"

        impact_templates = {
            CATEGORY_TRAFFIC: (
                f"Traffic routing disrupted — {kind} configuration "
                f"prevents correct request delivery"
            ),
            CATEGORY_DATA: (
                f"Data dependency broken — {kind} references may "
                f"cause Pod crash-loops on deployment"
            ),
            CATEGORY_RESOURCE: (
                f"Resource exhaustion risk — {kind} can consume "
                f"unlimited cluster resources"
            ),
            CATEGORY_AVAILABILITY: (
                f"Availability risk — {kind} may not recover from "
                f"failures without health probes"
            ),
            CATEGORY_SECURITY: (
                f"Security posture weakness — {kind} does not meet "
                f"Pod Security Standards"
            ),
            CATEGORY_RBAC: (
                f"Authorization risk — {kind} may lack required "
                f"permissions at runtime"
            ),
            CATEGORY_VERSION: (
                f"Version compatibility risk — {kind} uses a deprecated "
                f"or removed API version"
            ),
            CATEGORY_ORPHAN: (
                f"Namespace clutter — {kind} is not referenced by "
                f"any workload"
            ),
            CATEGORY_HYGIENE: (
                f"Configuration hygiene — {kind} has a non-critical "
                f"best-practice suggestion"
            ),
            # Phase 2 categories
            CATEGORY_SCHEDULING: (
                f"Scheduling failure risk — {kind} references a missing "
                f"PriorityClass or RuntimeClass, Pod may stay Pending"
            ),
            CATEGORY_NETWORK_ISOLATION: (
                f"Network isolation risk — {kind} NetworkPolicy has a "
                f"broken selector, leaving pods unprotected or blocked"
            ),
            CATEGORY_DISRUPTION: (
                f"Disruption tolerance risk — {kind} PDB misconfiguration "
                f"removes protection during node drains and upgrades"
            ),
            CATEGORY_IMAGE: (
                f"Image pull failure — {kind} references an invalid or "
                f"unreachable container image, deployment will fail"
            ),
            CATEGORY_CRD: (
                f"CRD dependency risk — {kind} custom resource will be "
                f"silently ignored without its CRD installed"
            ),
            CATEGORY_REPLICA: (
                f"Replica configuration risk — {kind} has a problematic "
                f"replica count or conflicting scaling constraints"
            ),
        }

        base = impact_templates.get(category, f"{kind} has a configuration issue")

        if scope > 0:
            base += f" (affects {scope} dependent resource{'s' if scope != 1 else ''})"

        return base

    def _build_node_key(self, finding: AnalysisResult) -> Optional[str]:
        """Build a graph node key from a finding's resource info.

        Why: Enables graph lookup for blast-radius calculation.
             Returns None if the finding lacks sufficient identity data.
        """
        kind = finding.resource_kind
        name = finding.resource_name
        if not kind or not name:
            return None

        # Extract namespace from resource_name if it contains '/'
        if "/" in name:
            parts = name.split("/", 1)
            return f"{kind}/{parts[0]}/{parts[1]}"

        return f"{kind}/default/{name}"
