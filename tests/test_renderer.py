from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


@patch('yamlr.ui.theme.console.print')
def test_render_welcome(mock_print):
    RichRenderer.render_welcome("/tmp", "1.30")
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_explain_dossier(mock_print):
    data = {"title": "Test", "definition": "Def", "rationale": "Rat", "impact": "High"}
    RichRenderer.render_explain("TEST", data)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_explain_k8s(mock_print):
    RichRenderer.render_explain("deployment.spec", None)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_summary(mock_print):
    stats = {"total_files": 10, "verified": 8, "violations": 2, "healed": 1, "time_ms": 150}
    RichRenderer.render_summary(stats)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_precision_help(mock_print):
    categories = {"Core": [{"name": "scan", "purpose": "Audit"}]}
    RichRenderer.render_precision_help(categories)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_graph(mock_print):
    edge = MagicMock(source="A", target="B", edge_type="DEPENDS")
    RichRenderer.render_graph([edge])
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_side_by_side_diff(mock_print):
    RichRenderer.render_side_by_side_diff("old", "new")
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_batch_summary(mock_print):
    res = MagicMock(violations=[], integrity_violations=[])
    report = MagicMock(results=[res], total_files=1, total_time_ms=100)
    RichRenderer.render_batch_summary(report, apply=True)
    mock_print.assert_called()

@patch('yamlr.ui.theme.console.print')
def test_render_score_animation(mock_print):
    res = MagicMock(health_score=85.0)
    report = MagicMock(results=[res])
    # Mock time.sleep to speed up test
    with patch('time.sleep'):
        RichRenderer.render_score_animation(report)
    mock_print.assert_called()
