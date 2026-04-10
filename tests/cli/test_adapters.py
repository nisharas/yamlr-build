from unittest.mock import patch

import pytest

from yamlr.core.engine.adapter_contracts import AdapterContract, ContractViolationError
from yamlr.core.engine.adapter_handler import apply_enterprise_pro_adapters


class DummyEngineNoDeletions:
    def __init__(self, path):
        self.adapters = {"test-rule": {"contract": "NO_DELETIONS"}}

    def get_contract(self, r):
        return "NO_DELETIONS"

    def execute_adapter(self, r, doc):
        return {"apiVersion": "apps/v1", "kind": "Deployment", "spec": {"template": {}}}


def test_contract_no_deletions():
    with patch("yamlr.pro.compliance.adapters.AdapterEngine", DummyEngineNoDeletions):
        original_yaml = """
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 3
  template: {}
        """
        findings = [{"rule_id": "test-rule"}]
        logs = []
        healed = apply_enterprise_pro_adapters(original_yaml, findings, logs, "/tmp/fake")
        assert "replicas: 3" in healed
        assert any("Contract Violation" in log for log in logs)
        assert any("Field deleted" in log for log in logs)


class DummyEngineSelectors:
    def __init__(self, path):
        self.adapters = {"test-rule": {"contract": "SELECTORS_FROZEN"}}

    def get_contract(self, r):
        return "SELECTORS_FROZEN"

    def execute_adapter(self, r, doc):
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"labels": {"app": "foo"}},
            "spec": {"selector": {"matchLabels": {"app": "mutated"}}},
        }


def test_contract_selectors_frozen():
    with patch("yamlr.pro.compliance.adapters.AdapterEngine", DummyEngineSelectors):
        original_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: foo
spec:
  selector:
    matchLabels:
      app: foo
        """
        findings = [{"rule_id": "test-rule"}]
        logs = []
        healed = apply_enterprise_pro_adapters(original_yaml, findings, logs, "/tmp/fake")
        assert "app: mutated" not in healed
        assert any("Contract Violation" in log for log in logs)
        assert any("Selector modified" in log for log in logs)


class DummyEngineAddOnly:
    def __init__(self, path):
        self.adapters = {"test-rule": {"contract": "ADD_ONLY"}}

    def get_contract(self, r):
        return "ADD_ONLY"

    def execute_adapter(self, r, doc):
        return {"apiVersion": "v1", "kind": "Pod", "metadata": {"labels": {"new": "label"}}}


def test_shadow_mode():
    with patch("yamlr.pro.compliance.adapters.AdapterEngine", DummyEngineAddOnly):
        original_yaml = """
apiVersion: v1
kind: Pod
metadata: {}
        """
        findings = [{"rule_id": "test-rule"}]
        logs = []
        healed = apply_enterprise_pro_adapters(original_yaml, findings, logs, "/tmp/fake", shadow_mode=True)
        assert "new: label" not in healed
        assert any("Shadow Mode" in log for log in logs)
