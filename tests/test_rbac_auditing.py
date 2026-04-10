import pytest

from yamlr.analyzers.rules import Rules
from yamlr.healers.best_practices.rbac import RBACAuditor


class MockContext:
    def __init__(self):
        self.findings = []

    def add_finding(self, finding):
        self.findings.append(finding)


@pytest.fixture
def auditor():
    return RBACAuditor()


@pytest.fixture
def mock_context():
    return MockContext()


def test_rbac_wildcard_detection(auditor, mock_context):
    doc = {
        "kind": "ClusterRole",
        "metadata": {"name": "admin-all"},
        "rules": [{"apiGroups": ["*"], "resources": ["*"], "verbs": ["*"]}],
    }
    auditor.heal_doc(doc, mock_context)

    wildcard_findings = [f for f in mock_context.findings if f.rule_id == Rules.RBAC_WILDCARD]
    assert len(wildcard_findings) > 0
    assert "Wildcard detected" in wildcard_findings[0].message


def test_rbac_sensitive_resource(auditor, mock_context):
    doc = {
        "kind": "Role",
        "metadata": {"name": "secret-reader"},
        "rules": [{"apiGroups": [""], "resources": ["secrets"], "verbs": ["get", "list"]}],
    }
    auditor.heal_doc(doc, mock_context)

    sensitive_findings = [f for f in mock_context.findings if f.rule_id == Rules.RBAC_SENSITIVE_RESOURCE]
    assert len(sensitive_findings) > 0
    assert "Sensitive access" in sensitive_findings[0].message


def test_rbac_suspicious_binding(auditor, mock_context):
    doc = {
        "kind": "ClusterRoleBinding",
        "metadata": {"name": "public-access"},
        "subjects": [{"kind": "Group", "name": "system:authenticated", "apiGroup": "rbac.authorization.k8s.io"}],
        "roleRef": {"kind": "ClusterRole", "name": "cluster-admin", "apiGroup": "rbac.authorization.k8s.io"},
    }
    auditor.heal_doc(doc, mock_context)

    binding_findings = [f for f in mock_context.findings if f.rule_id == Rules.RBAC_SUSPICIOUS_BINDING]
    assert len(binding_findings) > 0
    assert "broad system group" in binding_findings[0].message


def test_rbac_privilege_escalation(auditor, mock_context):
    doc = {
        "kind": "Role",
        "metadata": {"name": "rbac-manager"},
        "rules": [{"apiGroups": ["rbac.authorization.k8s.io"], "resources": ["roles"], "verbs": ["bind", "escalate"]}],
    }
    auditor.heal_doc(doc, mock_context)

    # Expect RBAC_PRIVILEGE_ESCALATION finding
    escalation_findings = [f for f in mock_context.findings if f.rule_id == Rules.RBAC_PRIVILEGE_ESCALATION]
    assert len(escalation_findings) > 0
    assert "risky verbs" in escalation_findings[0].message


def test_rbac_wildcard_remediation(auditor, mock_context):
    doc = {
        "kind": "Role",
        "metadata": {"name": "wildcard-role"},
        "rules": [{"apiGroups": [""], "resources": ["pods"], "verbs": ["*"]}],
    }
    # Test with harden=True
    modified = auditor.heal_doc(doc, mock_context, harden=True)

    assert modified is True
    assert "*" not in doc["rules"][0]["verbs"]
    assert "get" in doc["rules"][0]["verbs"]
    assert "list" in doc["rules"][0]["verbs"]
