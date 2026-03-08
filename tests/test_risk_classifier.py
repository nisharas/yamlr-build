#!/usr/bin/env python3
"""
Yamlr RISK CLASSIFIER TEST SUITE
-----------------------------------
Tests for heuristic risk classification, category assignment,
impact description generation, and graph-aware scope calculation.

Why: Risk classification drives the Safety Engine's CLI output.
     False risk levels erode trust — every heuristic must be verified.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-28
"""

import pytest
from dataclasses import field
from yamlr.analyzers.base import AnalysisResult
from yamlr.analyzers.risk_classifier import (
    RiskClassifier,
    RiskAssessment,
    CATEGORY_TRAFFIC,
    CATEGORY_DATA,
    CATEGORY_RESOURCE,
    CATEGORY_AVAILABILITY,
    CATEGORY_SECURITY,
    CATEGORY_RBAC,
    CATEGORY_VERSION,
    CATEGORY_ORPHAN,
    CATEGORY_HYGIENE,
    CATEGORY_SCHEDULING,
    CATEGORY_NETWORK_ISOLATION,
    CATEGORY_DISRUPTION,
    CATEGORY_IMAGE,
    CATEGORY_CRD,
    CATEGORY_REPLICA,
)
from yamlr.core.resource_graph import ResourceGraph
from yamlr.models import ManifestIdentity


# =====================================================================
# FIXTURES
# =====================================================================


def _make_finding(
    rule_id: str = "",
    resource_kind: str = "Deployment",
    resource_name: str = "my-dep",
    severity: str = "WARNING",
    analyzer_name: str = "test",
    message: str = "",
    **kwargs,
) -> AnalysisResult:
    """Helper to construct AnalysisResult for testing."""
    return AnalysisResult(
        analyzer_name=analyzer_name,
        severity=severity,
        message=message,
        resource_name=resource_name,
        resource_kind=resource_kind,
        file_path="test.yaml",
        rule_id=rule_id,
        **kwargs,
    )


def _make_identity(
    kind: str, name: str, namespace: str = "default", **kwargs
) -> ManifestIdentity:
    """Helper to construct ManifestIdentity for testing."""
    if "api_version" not in kwargs:
        kwargs["api_version"] = "v1"
    return ManifestIdentity(
        kind=kind, name=name, namespace=namespace,
        **kwargs,
    )


@pytest.fixture
def classifier():
    """Fresh RiskClassifier instance."""
    return RiskClassifier()


@pytest.fixture
def graph_with_ingress():
    """Graph with Ingress→Service→Deployment chain."""
    graph = ResourceGraph()
    graph.build([
        _make_identity(
            "Ingress", "web-ingress",
            api_version="networking.k8s.io/v1",
            ingress_backends=[{"service": "api-svc", "port": "80"}],
        ),
        _make_identity(
            "Service", "api-svc",
            selector={"app": "api"},
            service_ports=[{"port": "80", "targetPort": "3000"}],
        ),
        _make_identity(
            "Deployment", "api-dep",
            api_version="apps/v1",
            labels={"app": "api"},
            container_ports=["3000"],
        ),
    ])
    return graph


# =====================================================================
# CATEGORIZATION
# =====================================================================


class TestCategorization:
    """Tests for risk category assignment."""

    def test_ghost_service_is_traffic(self, classifier):
        """Ghost service rule_id → Traffic Routing Failure."""
        finding = _make_finding(rule_id="ghost_service")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_TRAFFIC

    def test_selector_mismatch_is_traffic(self, classifier):
        """Selector mismatch → Traffic Routing Failure."""
        finding = _make_finding(rule_id="selector_mismatch")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_TRAFFIC

    def test_port_rule_is_traffic(self, classifier):
        """Port-related rule → Traffic Routing Failure."""
        finding = _make_finding(rule_id="port_mismatch")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_TRAFFIC

    def test_configmap_ref_is_data(self, classifier):
        """ConfigMap reference → Data Dependency Risk."""
        finding = _make_finding(rule_id="missing_configmap")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_DATA

    def test_pvc_ref_is_data(self, classifier):
        """PVC reference → Data Dependency Risk."""
        finding = _make_finding(rule_id="broken_pvc_volume")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_DATA

    def test_resource_limit_is_resource(self, classifier):
        """Resource limit rule → Resource Exhaustion Risk."""
        finding = _make_finding(rule_id="missing_resource_limits")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_RESOURCE

    def test_probe_is_availability(self, classifier):
        """Probe rule → Availability Risk."""
        finding = _make_finding(rule_id="missing_liveness_probe")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_AVAILABILITY

    def test_security_rule_is_security(self, classifier):
        """Security rule → Security Posture Weakness."""
        finding = _make_finding(rule_id="privilege_escalation")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_SECURITY

    def test_security_analyzer_is_security(self, classifier):
        """Security analyzer name → Security category."""
        finding = _make_finding(analyzer_name="security_hardening")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_SECURITY

    def test_rbac_rule_is_rbac(self, classifier):
        """RBAC rule → Authorization Failure Risk."""
        finding = _make_finding(rule_id="broken_role_binding")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_RBAC

    def test_deprecated_is_version(self, classifier):
        """Deprecated API rule → Version Compatibility Risk."""
        finding = _make_finding(rule_id="deprecated_api")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_VERSION

    def test_deprecation_message_is_version(self, classifier):
        """Message containing 'deprecated' → Version category."""
        finding = _make_finding(message="API is deprecated in v1.25")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_VERSION

    def test_orphan_is_orphan(self, classifier):
        """Orphan rule → Namespace Clutter."""
        finding = _make_finding(rule_id="orphan_configmap")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_ORPHAN

    def test_unknown_is_hygiene(self, classifier):
        """Unrecognized rule → Configuration Hygiene (default)."""
        finding = _make_finding(rule_id="custom_unknown_rule")
        assessment = classifier.classify(finding)
        assert assessment.category == CATEGORY_HYGIENE


# =====================================================================
# RISK SCORING
# =====================================================================


class TestRiskScoring:
    """Tests for priority-ordered heuristic rules."""

    def test_ingress_affected_is_high(self, classifier, graph_with_ingress):
        """Ingress-affecting finding → HIGH."""
        finding = _make_finding(
            rule_id="ghost_service",
            resource_kind="Service",
            resource_name="api-svc",
        )
        assessment = classifier.classify(finding, graph_with_ingress)
        assert assessment.risk_level == "HIGH"

    def test_multi_workload_is_high(self, classifier):
        """3+ affected workloads → HIGH."""
        graph = ResourceGraph()
        identities = [_make_identity("ConfigMap", "shared-config")]
        identities.extend([
            _make_identity(
                "Deployment", f"dep-{i}",
                api_version="apps/v1",
                config_refs=["shared-config"],
            )
            for i in range(4)
        ])
        graph.build(identities)
        finding = _make_finding(
            rule_id="missing_configmap",
            resource_kind="ConfigMap",
            resource_name="shared-config",
        )
        assessment = classifier.classify(finding, graph)
        assert assessment.risk_level == "HIGH"

    def test_single_workload_is_medium(self, classifier, graph_with_ingress):
        """Single workload impact → MEDIUM."""
        finding = _make_finding(
            rule_id="missing_resource_limits",
            resource_kind="Deployment",
            resource_name="api-dep",
        )
        assessment = classifier.classify(finding, graph_with_ingress)
        # Resource limits category defaults to MEDIUM
        assert assessment.risk_level == "MEDIUM"

    def test_cosmetic_is_low(self, classifier):
        """Cosmetic finding with no graph → LOW."""
        finding = _make_finding(rule_id="missing_labels")
        assessment = classifier.classify(finding)
        assert assessment.risk_level == "LOW"

    def test_security_error_is_high(self, classifier):
        """Security ERROR → HIGH."""
        finding = _make_finding(
            rule_id="privilege_escalation",
            severity="ERROR",
        )
        assessment = classifier.classify(finding)
        assert assessment.risk_level == "HIGH"

    def test_traffic_without_graph_is_medium(self, classifier):
        """Traffic category without graph data → MEDIUM."""
        finding = _make_finding(rule_id="ghost_service")
        assessment = classifier.classify(finding)
        assert assessment.risk_level == "MEDIUM"


# =====================================================================
# IMPACT DESCRIPTIONS
# =====================================================================


class TestImpactDescriptions:
    """Tests for human-readable impact description generation."""

    def test_traffic_impact_description(self, classifier):
        """Traffic category generates routing disruption message."""
        finding = _make_finding(rule_id="ghost_service", resource_kind="Service")
        assessment = classifier.classify(finding)
        assert "Traffic routing disrupted" in assessment.impact_description
        assert "Service" in assessment.impact_description

    def test_scope_appended_to_description(self, classifier, graph_with_ingress):
        """Scope count is appended to impact description."""
        finding = _make_finding(
            rule_id="ghost_service",
            resource_kind="Service",
            resource_name="api-svc",
        )
        assessment = classifier.classify(finding, graph_with_ingress)
        if assessment.scope_count > 0:
            assert "affects" in assessment.impact_description

    def test_data_impact_description(self, classifier):
        """Data category generates crash-loop warning."""
        finding = _make_finding(rule_id="missing_configmap")
        assessment = classifier.classify(finding)
        assert "Data dependency" in assessment.impact_description


# =====================================================================
# GRAPH INTEGRATION
# =====================================================================


class TestGraphIntegration:
    """Tests for graph-aware scope calculation."""

    def test_scope_from_graph(self, classifier, graph_with_ingress):
        """Scope count reflects graph blast radius."""
        finding = _make_finding(
            rule_id="ghost_service",
            resource_kind="Service",
            resource_name="api-svc",
        )
        assessment = classifier.classify(finding, graph_with_ingress)
        assert assessment.scope_count >= 1

    def test_no_graph_zero_scope(self, classifier):
        """Without graph, scope is zero."""
        finding = _make_finding(rule_id="ghost_service")
        assessment = classifier.classify(finding, None)
        assert assessment.scope_count == 0

    def test_affected_resources_populated(self, classifier, graph_with_ingress):
        """Affected resources list is populated from graph."""
        finding = _make_finding(
            rule_id="ghost_service",
            resource_kind="Service",
            resource_name="api-svc",
        )
        assessment = classifier.classify(finding, graph_with_ingress)
        assert isinstance(assessment.affected_resources, list)


# =====================================================================
# ENRICH FINDING
# =====================================================================


class TestEnrichFinding:
    """Tests for the enrich_finding convenience method."""

    def test_enrich_populates_fields(self, classifier):
        """enrich_finding sets all safety-oriented fields."""
        finding = _make_finding(rule_id="ghost_service")
        classifier.enrich_finding(finding)
        assert finding.risk_level != "UNKNOWN"
        assert finding.risk_category != "Uncategorized"
        assert finding.impact_description is not None

    def test_enrich_returns_same_finding(self, classifier):
        """enrich_finding returns the same finding object."""
        finding = _make_finding(rule_id="ghost_service")
        result = classifier.enrich_finding(finding)
        assert result is finding


# =====================================================================
# NEW CATEGORIES (Phase 2 — EPIC-23)
# =====================================================================


class TestSchedulingCategory:
    """Tests for CATEGORY_SCHEDULING."""

    def test_priorityclass_rule_id(self, classifier):
        """priorityclass in rule_id → Scheduling."""
        finding = _make_finding(rule_id="missing_priorityclass")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_SCHEDULING

    def test_runtimeclass_kind(self, classifier):
        """RuntimeClass kind → Scheduling."""
        finding = _make_finding(rule_id="config_issue", resource_kind="RuntimeClass")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_SCHEDULING

    def test_scheduling_risk_medium(self, classifier):
        """Scheduling issues → MEDIUM risk."""
        finding = _make_finding(rule_id="missing_priorityclass")
        result = classifier.classify(finding)
        assert result.risk_level == "MEDIUM"


class TestNetworkIsolationCategory:
    """Tests for CATEGORY_NETWORK_ISOLATION."""

    def test_networkpolicy_rule_id(self, classifier):
        """networkpolicy in rule_id → Network Isolation."""
        finding = _make_finding(rule_id="networkpolicy_mismatch")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_NETWORK_ISOLATION

    def test_networkpolicy_kind(self, classifier):
        """NetworkPolicy kind → Network Isolation."""
        finding = _make_finding(rule_id="np_check", resource_kind="NetworkPolicy")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_NETWORK_ISOLATION

    def test_network_isolation_always_high(self, classifier):
        """Network isolation → always HIGH (security incident)."""
        finding = _make_finding(rule_id="networkpolicy_unmatched")
        result = classifier.classify(finding)
        assert result.risk_level == "HIGH"


class TestDisruptionCategory:
    """Tests for CATEGORY_DISRUPTION."""

    def test_pdb_rule_id(self, classifier):
        """pdb in rule_id → Disruption Tolerance."""
        finding = _make_finding(rule_id="pdb_selector_mismatch")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_DISRUPTION

    def test_pdb_kind(self, classifier):
        """PodDisruptionBudget kind → Disruption."""
        finding = _make_finding(rule_id="budget_check", resource_kind="PodDisruptionBudget")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_DISRUPTION

    def test_disruption_risk_medium(self, classifier):
        """Disruption tolerance → MEDIUM risk."""
        finding = _make_finding(rule_id="pdb_misconfigured")
        result = classifier.classify(finding)
        assert result.risk_level == "MEDIUM"


class TestImageCategory:
    """Tests for CATEGORY_IMAGE."""

    def test_image_rule_id(self, classifier):
        """image in rule_id → Image Pull Failure."""
        finding = _make_finding(rule_id="invalid_image_tag")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_IMAGE

    def test_image_pull_message(self, classifier):
        """'image pull' in message → Image Pull Failure."""
        finding = _make_finding(rule_id="deploy_check", message="image pull error detected")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_IMAGE

    def test_image_always_high(self, classifier):
        """Image pull failure → always HIGH (100% failure)."""
        finding = _make_finding(rule_id="invalid_image_tag")
        result = classifier.classify(finding)
        assert result.risk_level == "HIGH"


class TestCRDCategory:
    """Tests for CATEGORY_CRD."""

    def test_crd_rule_id(self, classifier):
        """crd in rule_id → CRD Dependency."""
        finding = _make_finding(rule_id="missing_crd")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_CRD

    def test_crd_kind(self, classifier):
        """CustomResourceDefinition kind → CRD."""
        finding = _make_finding(rule_id="config_issue", resource_kind="CustomResourceDefinition")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_CRD

    def test_crd_risk_medium(self, classifier):
        """CRD dependency → MEDIUM risk."""
        finding = _make_finding(rule_id="missing_crd")
        result = classifier.classify(finding)
        assert result.risk_level == "MEDIUM"


class TestReplicaCategory:
    """Tests for CATEGORY_REPLICA."""

    def test_replica_rule_id(self, classifier):
        """replica in rule_id → Replica Config."""
        finding = _make_finding(rule_id="zero_replicas")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_REPLICA

    def test_replicas_zero_message(self, classifier):
        """'replicas zero' in message → Replica Config."""
        finding = _make_finding(rule_id="config_check", message="replicas set to zero")
        result = classifier.classify(finding)
        assert result.category == CATEGORY_REPLICA

    def test_replica_risk_medium(self, classifier):
        """Replica config → MEDIUM risk."""
        finding = _make_finding(rule_id="zero_replicas")
        result = classifier.classify(finding)
        assert result.risk_level == "MEDIUM"
