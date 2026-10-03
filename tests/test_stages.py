"""Unit Tests for Core Stages."""
from collections import namedtuple

from yamlr.core.stages import (
    HealthScoringStage,
    IntegrityAuditStage,
    SchemaValidationStage,
    TopologyAnalysisStage,
)

MockViolation = namedtuple("MockViolation", ["severity", "message"])


def test_health_scoring_stage_calculation():
    """Validates deterministic scoring math for various severity tiers."""
    # Clean baseline
    assert HealthScoringStage.calculate_score([]) == 100.0

    # 1 Critical (-15.0) -> 85.0
    crit = [MockViolation(severity="CRITICAL", message="root user")]
    assert HealthScoringStage.calculate_score(crit) == 85.0

    # 1 High (-5.0) -> 95.0
    high = [MockViolation(severity="HIGH", message="missing limits")]
    assert HealthScoringStage.calculate_score(high) == 95.0

    # 1 Medium (-2.0) -> 98.0
    med = [MockViolation(severity="MEDIUM", message="floating tag")]
    assert HealthScoringStage.calculate_score(med) == 98.0

    # 1 Low (-0.5) -> 99.5
    low = [MockViolation(severity="LOW", message="missing comment")]
    assert HealthScoringStage.calculate_score(low) == 99.5

    # Floor clamping at 0.0
    many_crits = [MockViolation(severity="CRITICAL", message="fatal")] * 10
    assert HealthScoringStage.calculate_score(many_crits) == 0.0


def test_topology_analysis_stage_boundary():
    """Validates topology analysis returns empty on single or empty resource list."""
    assert TopologyAnalysisStage.analyze([]) == []

    # Single dummy result
    SingleResult = namedtuple("SingleResult", ["identity"])
    assert TopologyAnalysisStage.analyze([SingleResult(identity=None)]) == []


def test_schema_validation_stage_empty_inputs():
    """Validates that SchemaValidationStage safely handles empty inputs."""
    assert SchemaValidationStage.validate(None, "", [], None) == []


def test_integrity_audit_stage_empty_inputs():
    """Validates that IntegrityAuditStage safely handles empty inputs."""
    assert IntegrityAuditStage.audit(None, []) == []
