
import pytest
import json
from unittest.mock import MagicMock, patch
from yamlr.core.idp_exporter import IDPExporter
from yamlr.core.scoring import AppSafetyReport, AppSafetySummary

def test_port_exporter_output():
    """Verify that Port exporter produces valid JSON with correct properties."""
    summary = AppSafetySummary(app_name="auth-service", score=85.0, top_rules=["rule-1"])
    report = AppSafetyReport(apps=[summary], overall_score=85.0)
    exporter = IDPExporter(report)
    
    port_json = exporter.export_port()
    data = json.loads(port_json)
    
    assert isinstance(data, list)
    assert data[0]["identifier"] == "auth-service"
    assert data[0]["properties"]["yamlr_score"] == 85.0
    assert data[0]["properties"]["yamlr_status"] == "healthy"

def test_pagerduty_exporter_output():
    """Verify that PagerDuty exporter alerts on critical scores."""
    summary = AppSafetySummary(app_name="critical-app", score=45.0)
    report = AppSafetyReport(apps=[summary], overall_score=45.0)
    exporter = IDPExporter(report)
    
    pd_json = exporter.export_pagerduty()
    data = json.loads(pd_json)
    
    assert data["payload"]["severity"] == "critical"
    assert "critical-app" in data["payload"]["custom_details"]["apps"]

def test_pydantic_json_compatibility():
    """Verify that export_json works regardless of Pydantic Version."""
    report = MagicMock()
    # Simulate Pydantic V2
    report.model_dump_json.return_value = '{"v2": true}'
    exporter = IDPExporter(report)
    assert exporter.export_json() == '{"v2": true}'
    
    # Simulate Pydantic V1
    del report.model_dump_json
    report.json.return_value = '{"v1": true}'
    assert exporter.export_json() == '{"v1": true}'

if __name__ == "__main__":
    pytest.main([__file__])
