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
        """Determine the risk category from finding attributes.

        Why: Category drives the "safety-audit tone" in CLI output.
             "Traffic Routing Failure" is more actionable than "ERROR".

        Heuristic: Match on analyzer_name, rule_id, and resource_kind.
        """
        analyzer = (finding.analyzer_name or "").lower()
        rule_id = (finding.rule_id or "").lower()
        kind = (finding.resource_kind or "").lower()
        message = (finding.message or "").lower()

        # --- SPECIFIC RESOURCE CHECKS FIRST ---
        # (Must precede generic "selector" traffic catch-all)

        # Network isolation (NetworkPolicy uses selectors but isn't traffic)
        if "networkpolicy" in rule_id or "network_policy" in rule_id:
            return CATEGORY_NETWORK_ISOLATION
        if kind == "networkpolicy":
            return CATEGORY_NETWORK_ISOLATION

        # Disruption tolerance (PDB uses selectors but isn't traffic)
        if "pdb" in rule_id or "disruption" in rule_id:
            return CATEGORY_DISRUPTION
        if kind == "poddisruptionbudget":
            return CATEGORY_DISRUPTION

        # Image pull failure (check before data dependency)
        if any(kw in rule_id for kw in ("image", "pull", "registry", "tag")):
            return CATEGORY_IMAGE
        if "imagepull" in message or "image pull" in message:
            return CATEGORY_IMAGE

        # --- GENERIC TRAFFIC CHECK ---
        if any(kw in rule_id for kw in ("ghost", "selector", "port", "ingress")):
            return CATEGORY_TRAFFIC
        if kind in ("service", "ingress", "httproute") and "mismatch" in message:
            return CATEGORY_TRAFFIC
        if "gateway" in rule_id or "httproute" in rule_id:
            return CATEGORY_TRAFFIC

        # Orphan/hygiene (check BEFORE data dependency — "orphan_configmap"
        # must match orphan, not configmap)
        if "orphan" in rule_id or "orphan" in message:
            return CATEGORY_ORPHAN

        # Replica configuration
        if any(kw in rule_id for kw in ("replica", "replicas", "scale")):
            return CATEGORY_REPLICA
        if "replicas" in message and ("zero" in message or "0" in message):
            return CATEGORY_REPLICA

        # Scheduling
        if any(kw in rule_id for kw in (
            "priorityclass", "priority_class", "runtimeclass",
            "runtime_class", "toleration", "nodeselector", "affinity",
        )):
            return CATEGORY_SCHEDULING
        if kind in ("priorityclass", "runtimeclass"):
            return CATEGORY_SCHEDULING

        # CRD dependency
        if any(kw in rule_id for kw in ("crd", "customresource", "custom_resource")):
            return CATEGORY_CRD
        if kind == "customresourcedefinition":
            return CATEGORY_CRD

        # Data dependency
        if any(kw in rule_id for kw in ("configmap", "secret", "pvc", "volume")):
            return CATEGORY_DATA
        if "missing" in message and kind in ("configmap", "secret"):
            return CATEGORY_DATA

        # Resource exhaustion
        if any(kw in rule_id for kw in ("limit", "resource", "cpu", "memory")):
            return CATEGORY_RESOURCE

        # Availability
        if any(kw in rule_id for kw in ("probe", "liveness", "readiness", "hpa")):
            return CATEGORY_AVAILABILITY

        # Security
        if any(kw in rule_id for kw in ("security", "privilege", "capabilities", "pss")):
            return CATEGORY_SECURITY
        if "harden" in analyzer or "security" in analyzer:
            return CATEGORY_SECURITY

        # RBAC
        if any(kw in rule_id for kw in ("rbac", "role", "binding", "serviceaccount")):
            return CATEGORY_RBAC

        # Version
        if any(kw in rule_id for kw in ("deprecated", "migration", "version", "api")):
            return CATEGORY_VERSION
        if "deprecat" in message:
            return CATEGORY_VERSION

        # Default
        return CATEGORY_HYGIENE

    def _score_risk(
        self, finding: AnalysisResult, assessment: RiskAssessment
    ) -> str:
        """Apply priority-ordered heuristic rules to determine risk level.

        Why: Explainable scoring. Each rule is documented and auditable.
             No hidden weights or ML black-box decisions.

        Rules (priority order — first match wins):
            1. Ingress/HTTPRoute-affecting → HIGH
            2. Multi-workload impact (scope ≥ 3) → HIGH
            3. Traffic category + any scope → HIGH
            4. Data category + scope > 0 → HIGH
            5. Security with ERROR severity → HIGH
            6. Network isolation category → HIGH
            7. Image pull failure → HIGH
            8. Gateway/HTTPRoute traffic-facing → HIGH
            9. Single workload impact → MEDIUM
            10. Resource/availability/version/scheduling → MEDIUM
            11. Disruption tolerance + scope > 0 → MEDIUM
            12. CRD dependency → MEDIUM
            13. Replica config → MEDIUM
            14. Cosmetic/hygiene → LOW
        """
        severity = (finding.severity or "").upper()
        category = assessment.category
        scope = assessment.scope_count

        # Rule 1: Ingress/HTTPRoute-affecting
        if category == CATEGORY_TRAFFIC and (
            "ingress" in (finding.resource_kind or "").lower()
            or "httproute" in (finding.resource_kind or "").lower()
            or any("Ingress" in r or "HTTPRoute" in r for r in assessment.affected_resources)
        ):
            return "HIGH"

        # Rule 2: Multi-workload impact
        if scope >= 3:
            return "HIGH"

        # Rule 3: Traffic category with any scope
        if category == CATEGORY_TRAFFIC and scope > 0:
            return "HIGH"

        # Rule 4: Data dependency with scope
        if category == CATEGORY_DATA and scope > 0:
            return "HIGH"

        # Rule 5: Security with ERROR severity
        if category == CATEGORY_SECURITY and severity == "ERROR":
            return "HIGH"

        # Rule 6: Network isolation = always HIGH (security incident)
        if category == CATEGORY_NETWORK_ISOLATION:
            return "HIGH"

        # Rule 7: Image pull failure = always HIGH (100% deployment failure)
        if category == CATEGORY_IMAGE:
            return "HIGH"

        # Rule 8: Gateway/HTTPRoute traffic-facing (same risk as Ingress)
        if category == CATEGORY_TRAFFIC and (
            "gateway" in (finding.rule_id or "").lower()
            or "httproute" in (finding.rule_id or "").lower()
        ):
            return "HIGH"

        # Rule 9: Single workload impact
        if scope >= 1:
            return "MEDIUM"

        # Rule 10: Resource/availability/version/scheduling
        if category in (
            CATEGORY_RESOURCE,
            CATEGORY_AVAILABILITY,
            CATEGORY_VERSION,
            CATEGORY_RBAC,
            CATEGORY_SCHEDULING,
        ):
            return "MEDIUM"

        # Rule 11: Disruption tolerance with scope
        if category == CATEGORY_DISRUPTION:
            return "MEDIUM"

        # Rule 12: CRD dependency (silent failure)
        if category == CATEGORY_CRD:
            return "MEDIUM"

        # Rule 13: Replica configuration (may be intentional)
        if category == CATEGORY_REPLICA:
            return "MEDIUM"

        # Rule 14: traffic/data/security without scope data
        if category in (CATEGORY_TRAFFIC, CATEGORY_DATA, CATEGORY_SECURITY):
            return "MEDIUM"

        # Default: Cosmetic/hygiene
        return "LOW"

    def _describe_impact(
        self, finding: AnalysisResult, assessment: RiskAssessment
    ) -> str:
        """Generate a human-readable impact description.

        Why: Impact descriptions transform "Missing field" into
             "Service will not route traffic." This is the identity shift.

        Strategy: Category-driven templates with scope injection.
        """
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
