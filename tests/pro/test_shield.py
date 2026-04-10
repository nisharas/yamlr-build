from unittest.mock import MagicMock

import pytest

from yamlr.models import ManifestIdentity
from yamlr.pro.shield import ShieldEngine


@pytest.fixture
def shield():
    return ShieldEngine()


def test_shield_shd_001_dangerous_hostpath(shield):
    doc = {
        "kind": "Pod",
        "metadata": {"name": "risk-pod"},
        "spec": {"volumes": [{"name": "root", "hostPath": {"path": "/etc/shadow"}}]},
    }
    findings = shield.detect_shadow_risks(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "SHD-001"
    assert "Dangerous HostPath" in findings[0].message


def test_shield_shd_002_privileged(shield):
    doc = {
        "kind": "Deployment",
        "metadata": {"name": "risk-deploy"},
        "spec": {"template": {"spec": {"containers": [{"name": "app", "securityContext": {"privileged": True}}]}}},
    }
    findings = shield.detect_shadow_risks(doc)
    assert any(f.rule_id == "SHD-002" for f in findings)
    assert "Privileged container" in next(f.message for f in findings if f.rule_id == "SHD-002")


def test_shield_shd_003_sensitive_volume_exposure(shield):
    doc = {
        "kind": "Pod",
        "metadata": {"name": "risk-pod"},
        "spec": {
            "volumes": [
                {"name": "root", "hostPath": {"path": "/var/log"}},
                {"name": "secret-vol", "secret": {"secretName": "my-secret"}},
            ]
        },
    }
    findings = shield.detect_shadow_risks(doc)
    assert any(f.rule_id == "SHD-003" for f in findings)
    assert "Sensitive volume" in next(f.message for f in findings if f.rule_id == "SHD-003")


def test_shield_shd_004_host_namespace(shield):
    doc = {"kind": "Pod", "metadata": {"name": "risk-pod"}, "spec": {"hostNetwork": True}}
    findings = shield.detect_shadow_risks(doc)
    assert any(f.rule_id == "SHD-004" for f in findings)


def test_shield_shd_005_resource_starvation_high_impact(shield):
    # Mocking graph for high-impact node
    mock_graph = MagicMock()
    mock_radius = MagicMock()
    mock_radius.risk_level = "HIGH"
    mock_graph.blast_radius.return_value = mock_radius

    doc = {
        "kind": "Pod",
        "metadata": {"name": "critical-pod"},
        "spec": {
            "containers": [{"name": "app", "image": "nginx"}]  # Missing limits
        },
    }
    findings = shield.detect_shadow_risks(doc, graph=mock_graph)
    assert any(f.rule_id == "SHD-005" for f in findings)
    assert "lacks resource limits" in next(f.message for f in findings if f.rule_id == "SHD-005")


def test_trust_score_calculation(shield):
    mock_context = MagicMock()
    mock_context.resource_graph = None  # Simple score

    # 10 findings * 0.5 penalty = 5 penalty -> 95.0
    score = shield.calculate_trust_score(mock_context, finding_risk_total=10)
    assert score == 95.0


def test_integrity_verification_positive(shield):
    # Valid YAML should have a valid DNA
    valid_yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: foo"
    assert shield.verify_integrity(valid_yaml) is True


def test_integrity_verification_empty(shield):
    assert shield.verify_integrity("") is False
    assert shield.verify_integrity("   ") is False
