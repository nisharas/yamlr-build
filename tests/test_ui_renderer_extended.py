from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.diff_engine import SideBySideDiff
from yamlr.ui.renderer import RichRenderer


@patch('yamlr.ui.renderer.console.print')
def test_render_explain(mock_print):
    RichRenderer.render_explain("query", {"title": "T", "definition": "D", "rationale": "R", "impact": "I", "example": "E"})
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_explain_k8s_field(mock_print):
    RichRenderer.render_explain("deployment.spec", None)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_explain_error(mock_print):
    RichRenderer.render_explain("query", None)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
@patch('yamlr.ui.renderer.Live')
def test_animate_integrity_scan(mock_live, mock_print):
    RichRenderer.animate_integrity_scan(50.0, 90.0)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_summary(mock_print):
    RichRenderer.render_summary({"total_files": 1, "verified": 1, "violations": 1, "pro_fixable": 1, "healed": 1, "time_ms": 10})
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_precision_help(mock_print):
    categories = {"Core Commands": [{"name": "scan", "purpose": "P"}]}
    RichRenderer.render_precision_help(categories, show_all=True)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_breadcrumb(mock_print):
    RichRenderer.render_breadcrumb("scan")
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_graph(mock_print):
    e1 = MagicMock(source="A", target="B", edge_type="deps")
    blast = MagicMock(source="A", affected_count=1, depth=1, risk_level="HIGH")
    RichRenderer.render_graph([e1], blast)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_integrity_ring(mock_print):
    RichRenderer.render_integrity_ring(95.0)
    RichRenderer.render_integrity_ring(80.0)
    RichRenderer.render_integrity_ring(60.0)
    assert mock_print.call_count == 3

@patch('yamlr.ui.renderer.console.print')
def test_render_side_by_side_diff(mock_print):
    with patch.object(SideBySideDiff, 'calculate', return_value=[("old", "new", "CHANGED"), ("old", None, "REMOVED"), (None, "new", "ADDED"), ("same", "same", "UNCHANGED")]):
        RichRenderer.render_side_by_side_diff("old\n", "new\n")
        assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_batch_summary(mock_print):
    res = MagicMock()
    res.violations = [1]
    res.integrity_violations = [1]
    report = MagicMock(results=[res], total_files=1, total_time_ms=10)
    RichRenderer.render_batch_summary(report, apply=True)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
@patch('time.sleep')
def test_render_score_animation(mock_sleep, mock_print):
    res = MagicMock(health_score=80.0)
    report = MagicMock(results=[res])
    RichRenderer.render_score_animation(report)
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_unified_diff(mock_print):
    RichRenderer.render_unified_diff("old\nline\n", "new\nline\n")
    assert mock_print.called
    RichRenderer.render_unified_diff("same", "same")
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_drift_report(mock_print):
    RichRenderer.render_drift_report(["Resource 'app' is broken"])
    assert mock_print.called
    RichRenderer.render_drift_report([])
    assert mock_print.called

@patch('yamlr.ui.renderer.console.print')
def test_render_audit_report(mock_print):
    RichRenderer.render_audit_report([{"sev": "CRITICAL", "type": "T", "msg": "M"}])
    assert mock_print.called
    RichRenderer.render_audit_report([])
    assert mock_print.called
