import pytest

from yamlr.analyzers.rules import Rules
from yamlr.healers.best_practices.privilege_escalation import PrivilegeEscalationAuditor


class MockContext:
    def __init__(self):
        self.findings = []

    def add_finding(self, finding):
        self.findings.append(finding)


@pytest.fixture
def auditor():
    return PrivilegeEscalationAuditor()


@pytest.fixture
def mock_context():
    return MockContext()


def test_audit_privileged_container(auditor, mock_context):
    doc = {
        "kind": "Deployment",
        "metadata": {"name": "privileged-app"},
        "spec": {
            "template": {
                "spec": {"containers": [{"name": "hacker", "image": "nginx", "securityContext": {"privileged": True}}]}
            }
        },
    }
    auditor.heal_doc(doc, mock_context)

    privileged_findings = [f for f in mock_context.findings if f.rule_id == Rules.PRIVILEGED_CONTAINER]
    assert len(privileged_findings) > 0
    assert "Privileged mode" in privileged_findings[0].message


def test_audit_run_as_root(auditor, mock_context):
    doc = {
        "kind": "Pod",
        "metadata": {"name": "root-pod"},
        "spec": {"securityContext": {"runAsUser": 0}, "containers": [{"name": "app", "image": "nginx"}]},
    }
    auditor.heal_doc(doc, mock_context)

    root_findings = [f for f in mock_context.findings if f.rule_id == Rules.RUN_AS_ROOT]
    assert len(root_findings) > 0
    assert "running as root" in root_findings[0].message


def test_audit_dangerous_capabilities(auditor, mock_context):
    doc = {
        "kind": "Pod",
        "metadata": {"name": "cap-pod"},
        "spec": {
            "containers": [
                {
                    "name": "scanner",
                    "image": "nmap",
                    "securityContext": {"capabilities": {"add": ["NET_ADMIN", "SYS_TIME"]}},
                }
            ]
        },
    }
    auditor.heal_doc(doc, mock_context)

    cap_findings = [f for f in mock_context.findings if f.rule_id == Rules.DANGEROUS_CAPABILITIES]
    assert len(cap_findings) > 0
    assert "NET_ADMIN" in cap_findings[0].message


def test_audit_sensitive_mount(auditor, mock_context):
    doc = {
        "kind": "Pod",
        "metadata": {"name": "docker-sock-pod"},
        "spec": {
            "volumes": [{"name": "docker-socket", "hostPath": {"path": "/var/run/docker.sock"}}],
            "containers": [{"name": "app", "image": "nginx"}],
        },
    }
    auditor.heal_doc(doc, mock_context)

    mount_findings = [f for f in mock_context.findings if f.rule_id == Rules.SENSITIVE_VOLUME_MOUNT]
    assert len(mount_findings) > 0
    assert "/var/run/docker.sock" in mount_findings[0].message


def test_remediate_privilege_escalation(auditor, mock_context):
    doc = {
        "kind": "Deployment",
        "metadata": {"name": "insecure-app"},
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "webapp",
                            "image": "nginx",
                            "securityContext": {"privileged": True, "allowPrivilegeEscalation": True},
                        }
                    ]
                }
            }
        },
    }
    # Test with harden=True
    modified = auditor.heal_doc(doc, mock_context, harden=True)

    assert modified is True
    sc = doc["spec"]["template"]["spec"]["containers"][0]["securityContext"]
    assert sc["privileged"] is False
    assert sc["allowPrivilegeEscalation"] is False
    assert "ALL" in [d.upper() for d in sc["capabilities"]["drop"]]
