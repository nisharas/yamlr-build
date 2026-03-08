import json
import pytest
from yamlr.core.io.sarif_formatter import SarifFormatter
from yamlr.models import HealFileResult

def test_sarif_formatter_injects_compliance_tags():
    """Verify that the SARIF formatter natively queries and injects Enterprise Compliance maps."""
    
    # Simulate a file result with a known SOC2/CIS violation
    finding1 = {
        "rule_id": "MissingNamespace",
        "severity": "WARNING",
        "message": "Resource is missing a namespace designation",
        "suggestion": "Add metadata.namespace"
    }
    
    finding2 = {
        "rule_id": "UnsafeHostPath",
        "severity": "ERROR",
        "message": "Pod specifies a hostPath volume, exposing the underlying node",
        "suggestion": "Change to emptyDir or a managed persistent volume"
    }

    res = HealFileResult(
        file_path="mock.yaml",
        full_path="/mock.yaml",
        success=False,
        status="WARNING",
        kind="Pod",
        logic_logs=[],
        findings=[finding1, finding2],
        health_score=50,
        identities=[],
    )

    formatter = SarifFormatter()
    sarif_json = formatter.format([res])
    
    sarif_data = json.loads(sarif_json)
    
    # Validate SARIF structure
    assert "runs" in sarif_data
    run = sarif_data["runs"][0]
    
    rules = run["tool"]["driver"]["rules"]
    assert len(rules) == 2
    
    # Verify MissingNamespace mapping
    namespace_rule = next((r for r in rules if r["id"] == "MissingNamespace"), None)
    assert namespace_rule is not None
    assert "properties" in namespace_rule
    assert "tags" in namespace_rule["properties"]
    assert "SOC2: CC6.1" in namespace_rule["properties"]["tags"]
    assert "CIS: 5.2.6" in namespace_rule["properties"]["tags"]
    
    # Verify UnsafeHostPath mapping
    hostpath_rule = next((r for r in rules if r["id"] == "UnsafeHostPath"), None)
    assert hostpath_rule is not None
    assert "properties" in hostpath_rule
    assert "tags" in hostpath_rule["properties"]
    assert "SOC2: CC6.1" in hostpath_rule["properties"]["tags"]
    assert "CIS: 5.2.3" in hostpath_rule["properties"]["tags"]
    
    # Verify Result Mapping
    results = run["results"]
    assert len(results) == 2
    assert results[0]["ruleId"] == "MissingNamespace"
    assert results[1]["ruleId"] == "UnsafeHostPath"

def test_sarif_formatter_graceful_missing_registry(monkeypatch):
    """Ensure OSS functionality remains intact if yamlr.pro is completely unavailable."""
    import sys
    
    # Mock the absence of the pro module
    monkeypatch.setitem(sys.modules, 'yamlr.pro.compliance.ruleset', None)
    
    finding = {
        "rule_id": "MissingNamespace",
        "severity": "WARNING",
        "message": "Resource is missing a namespace"
    }

    res = HealFileResult(
        file_path="mock.yaml",
        full_path="/mock.yaml",
        success=False,
        status="WARNING",
        kind="Pod",
        logic_logs=[],
        findings=[finding],
        health_score=50,
        identities=[],
    )

    formatter = SarifFormatter()
    sarif_json = formatter.format([res])
    sarif_data = json.loads(sarif_json)
    
    rules = sarif_data["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1
    namespace_rule = rules[0]
    
    # Should cleanly format the rule without breaking, but lack properties
    assert namespace_rule["id"] == "MissingNamespace"
    assert "properties" not in namespace_rule
