import json
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.sarif_reporter import SarifReporter


def test_generate_sarif_basic(tmp_path):
    """Test generating a simple SARIF report."""
    output_path = tmp_path / "report.sarif"
    
    mock_res = MagicMock()
    mock_res.file_path = "test.yaml"
    
    mock_integrity = MagicMock()
    mock_integrity.rule_id = "R-1"
    mock_integrity.check_name = "Check"
    mock_integrity.message = "Msg"
    mock_integrity.severity = "CRITICAL"
    mock_integrity.line_no = 5
    
    mock_res.integrity_violations = [mock_integrity]
    mock_res.violations = []
    
    SarifReporter.generate_sarif([mock_res], str(output_path))
    
    assert output_path.exists()
    with open(output_path, "r") as f:
        data = json.load(f)
        
    assert data["version"] == "2.1.0"
    assert len(data["runs"]) == 1
    assert data["runs"][0]["tool"]["driver"]["name"] == "yamlr"
    
    results = data["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "R-1"
    assert results[0]["level"] == "error"
    assert results[0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 5

def test_generate_sarif_schema_violations(tmp_path):
    """Test generating SARIF with schema violations."""
    output_path = tmp_path / "report2.sarif"
    
    mock_res = MagicMock()
    mock_res.file_path = "test2.yaml"
    mock_res.integrity_violations = []
    
    mock_schema = MagicMock()
    mock_schema.field_path = "spec.replicas"
    mock_schema.message = "Bad schema"
    mock_schema.severity = "HIGH"
    
    mock_res.violations = [mock_schema]
    
    SarifReporter.generate_sarif([mock_res], str(output_path))
    
    with open(output_path, "r") as f:
        data = json.load(f)
        
    results = data["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "SCHEMA-spec.replicas"
    assert results[0]["level"] == "error"

def test_generate_sarif_no_catalog_fallback(tmp_path):
    """Test SARIF generation when the catalog file is missing."""
    output_path = tmp_path / "report3.sarif"
    
    mock_res = MagicMock()
    mock_res.file_path = "test3.yaml"
    mock_res.integrity_violations = []
    mock_res.violations = []
    
    with patch('os.path.exists', return_value=False):
        SarifReporter.generate_sarif([mock_res], str(output_path))
        
    with open(output_path, "r") as f:
        data = json.load(f)
    assert len(data["runs"][0]["results"]) == 0

def test_map_severity():
    """Test severity mapping."""
    assert SarifReporter._map_severity("CRITICAL") == "error"
    assert SarifReporter._map_severity("HIGH") == "error"
    assert SarifReporter._map_severity("WARNING") == "warning"
    assert SarifReporter._map_severity("INFO") == "note"
    assert SarifReporter._map_severity("UNKNOWN") == "note"
