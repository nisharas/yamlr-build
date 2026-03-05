#!/usr/bin/env python3
"""
Yamlr VERSION INTELLIGENCE TEST SUITE
---------------------------------------
Tests for extended deprecation database, field-level deprecations,
upgrade risk scoring, and version coverage verification.

Why: Version intelligence prevents silent deployment failures.
     A missed removal entry means Yamlr gives users a false
     sense of safety — the worst possible outcome.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-28
"""

import pytest
from yamlr.core.deprecations import (
    DeprecationChecker,
    DeprecationInfo,
    DEPRECATED_APIS,
    DEPRECATED_FIELDS,
)


@pytest.fixture
def checker():
    """Fresh DeprecationChecker instance."""
    return DeprecationChecker()


# =====================================================================
# DATABASE COVERAGE
# =====================================================================


class TestDatabaseCoverage:
    """Verify deprecation database covers all stable K8s versions."""

    def test_has_entries_for_1_16_removals(self, checker):
        """K8s 1.16: extensions/v1beta1 Deployment removed."""
        info = checker.check("extensions/v1beta1", "Deployment")
        assert info is not None
        assert info.removed_in_version == "1.16"
        assert info.severity == "REMOVED"

    def test_has_entries_for_1_22_removals(self, checker):
        """K8s 1.22: networking.k8s.io/v1beta1 Ingress removed."""
        info = checker.check("networking.k8s.io/v1beta1", "Ingress")
        assert info is not None
        assert info.removed_in_version == "1.22"

    def test_has_entries_for_1_25_removals(self, checker):
        """K8s 1.25: policy/v1beta1 PodSecurityPolicy removed."""
        info = checker.check("policy/v1beta1", "PodSecurityPolicy")
        assert info is not None
        assert info.removed_in_version == "1.25"

    def test_has_entries_for_1_25_pdb(self, checker):
        """K8s 1.25: policy/v1beta1 PodDisruptionBudget removed."""
        info = checker.check("policy/v1beta1", "PodDisruptionBudget")
        assert info is not None
        assert info.removed_in_version == "1.25"

    def test_has_entries_for_1_26_removals(self, checker):
        """K8s 1.26: autoscaling/v2beta2 HPA removed."""
        info = checker.check("autoscaling/v2beta2", "HorizontalPodAutoscaler")
        assert info is not None
        assert info.removed_in_version == "1.26"

    def test_has_entries_for_1_27_removals(self, checker):
        """K8s 1.27: storage.k8s.io/v1beta1 CSIStorageCapacity removed."""
        info = checker.check("storage.k8s.io/v1beta1", "CSIStorageCapacity")
        assert info is not None
        assert info.removed_in_version == "1.27"

    def test_has_entries_for_1_29_flowcontrol_v1beta2(self, checker):
        """K8s 1.29: flowcontrol v1beta2 FlowSchema removed."""
        info = checker.check("flowcontrol.apiserver.k8s.io/v1beta2", "FlowSchema")
        assert info is not None
        assert info.removed_in_version == "1.29"

    def test_has_entries_for_1_29_flowcontrol_v1beta3(self, checker):
        """K8s 1.29: flowcontrol v1beta3 PriorityLevelConfiguration removed."""
        info = checker.check(
            "flowcontrol.apiserver.k8s.io/v1beta3", "PriorityLevelConfiguration"
        )
        assert info is not None

    def test_has_entries_for_1_33_validating_admission(self, checker):
        """K8s 1.33+: ValidatingAdmissionPolicy v1beta1 deprecated."""
        info = checker.check(
            "admissionregistration.k8s.io/v1beta1", "ValidatingAdmissionPolicy"
        )
        assert info is not None
        assert info.severity == "WARNING"
        assert info.replacement_api == "admissionregistration.k8s.io/v1"

    def test_has_entries_for_1_33_vap_binding(self, checker):
        """K8s 1.33+: ValidatingAdmissionPolicyBinding v1beta1 deprecated."""
        info = checker.check(
            "admissionregistration.k8s.io/v1beta1",
            "ValidatingAdmissionPolicyBinding",
        )
        assert info is not None
        assert info.severity == "WARNING"

    def test_total_entry_count_minimum(self):
        """Database should have at least 20 entries (comprehensive coverage)."""
        assert len(DEPRECATED_APIS) >= 20


# =====================================================================
# IS_REMOVED
# =====================================================================


class TestIsRemoved:
    """Tests for is_removed() method."""

    def test_extensions_v1beta1_removed_in_1_16(self, checker):
        """extensions/v1beta1 Deployment is removed at 1.16."""
        assert checker.is_removed("extensions/v1beta1", "Deployment", "1.16")

    def test_extensions_v1beta1_not_removed_in_1_15(self, checker):
        """extensions/v1beta1 Deployment is NOT removed at 1.15."""
        assert not checker.is_removed("extensions/v1beta1", "Deployment", "1.15")

    def test_warning_not_treated_as_removed(self, checker):
        """WARNING deprecations are NOT treated as removed."""
        assert not checker.is_removed(
            "admissionregistration.k8s.io/v1beta1",
            "ValidatingAdmissionPolicy",
            "1.35",
        )

    def test_unknown_api_returns_false(self, checker):
        """Unknown API returns False."""
        assert not checker.is_removed("unknown/v1", "Unknown", "1.30")


# =====================================================================
# FIELD-LEVEL DEPRECATIONS
# =====================================================================


class TestFieldDeprecations:
    """Tests for field-level deprecation tracking."""

    def test_spec_service_account_deprecated(self, checker):
        """spec.serviceAccount is deprecated."""
        info = checker.check_field("Pod", "spec.serviceAccount")
        assert info is not None
        assert info["replacement"] == "spec.serviceAccountName"
        assert info["deprecated_in"] == "1.16"

    def test_psp_wildcard_deprecated(self, checker):
        """PodSecurityPolicy wildcard is deprecated."""
        info = checker.check_field("PodSecurityPolicy", "*")
        assert info is not None
        assert info["removed_in"] == "1.25"

    def test_sidecar_containers_tracked(self, checker):
        """SidecarContainers GA field change is tracked."""
        info = checker.check_field("Pod", "spec.initContainers[].restartPolicy")
        assert info is not None
        assert "SidecarContainers" in info["note"]

    def test_unknown_field_returns_none(self, checker):
        """Unknown field returns None."""
        assert checker.check_field("Pod", "spec.nonExistentField") is None

    def test_field_deprecation_count(self):
        """Should have at least 3 field-level deprecation entries."""
        assert len(DEPRECATED_FIELDS) >= 3


# =====================================================================
# UPGRADE RISK SCORE
# =====================================================================


class TestUpgradeRiskScore:
    """Tests for upgrade_risk_score() method."""

    def test_1_24_to_1_29_has_removals(self, checker):
        """Upgrading 1.24→1.29 should find multiple removals."""
        result = checker.upgrade_risk_score("1.24", "1.29")
        assert result["removal_count"] >= 1
        assert result["risk_level"] in ("MEDIUM", "HIGH")

    def test_1_15_to_1_22_is_high_risk(self, checker):
        """Upgrading 1.15→1.22: many removals (1.16 + 1.22) → HIGH."""
        result = checker.upgrade_risk_score("1.15", "1.22")
        assert result["removal_count"] >= 3
        assert result["risk_level"] == "HIGH"

    def test_same_version_no_risk(self, checker):
        """Same version → NONE risk."""
        result = checker.upgrade_risk_score("1.28", "1.28")
        assert result["risk_level"] == "NONE"
        assert result["removal_count"] == 0

    def test_recent_upgrade_low_risk(self, checker):
        """Minor version bump within safe range → LOW or NONE."""
        result = checker.upgrade_risk_score("1.30", "1.31")
        assert result["risk_level"] in ("NONE", "LOW")

    def test_result_structure(self, checker):
        """Result contains expected keys."""
        result = checker.upgrade_risk_score("1.20", "1.28")
        assert "from_version" in result
        assert "to_version" in result
        assert "risk_level" in result
        assert "removal_count" in result
        assert "warning_count" in result
        assert "removals" in result
        assert "warnings" in result

    def test_removals_list_structure(self, checker):
        """Each removal entry has api, kind, removed_in fields."""
        result = checker.upgrade_risk_score("1.15", "1.22")
        if result["removals"]:
            entry = result["removals"][0]
            assert "api" in entry
            assert "kind" in entry
            assert "removed_in" in entry
