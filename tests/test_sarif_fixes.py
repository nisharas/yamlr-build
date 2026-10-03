"""Tests for SARIF 2.1.0 fixes objects with artifactChanges."""
import json
import tempfile
from unittest.mock import MagicMock

from yamlr.sarif_reporter import SarifReporter


def test_sarif_includes_fixes():
    """Verify SARIF generator attaches fixes objects to auto-repairable violations."""
    mock_res = MagicMock()
    mock_res.file_path = "deploy.yaml"
    mock_res.violations = []
    
    mock_iv = MagicMock()
    mock_iv.rule_id = "INT-001"
    mock_iv.check_name = "Image Immutability"
    mock_iv.message = "Container uses mutable image tag :latest"
    mock_iv.severity = "WARNING"
    mock_iv.line_no = 15
    mock_res.integrity_violations = [mock_iv]

    mock_fix = MagicMock()
    mock_fix.rule_id = "INT-001"
    mock_fix.field_path = "image"
    mock_fix.suggested_value = "nginx:1.25.3"
    mock_res.suggested_fixes = [mock_fix]

    with tempfile.NamedTemporaryFile(suffix=".sarif", delete=False) as tf:
        out_path = tf.name

    try:
        SarifReporter.generate_sarif([mock_res], out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = data["runs"][0]["results"]
        assert len(results) == 1
        res = results[0]
        assert res["ruleId"] == "INT-001"
        assert "fixes" in res
        fix_obj = res["fixes"][0]
        assert "artifactChanges" in fix_obj
        changes = fix_obj["artifactChanges"][0]
        assert changes["artifactLocation"]["uri"] == "deploy.yaml"
        assert len(changes["replacements"]) == 1
        assert "nginx:1.25.3" in changes["replacements"][0]["insertedContent"]["text"]
    finally:
        import os
        if os.path.exists(out_path):
            os.remove(out_path)
