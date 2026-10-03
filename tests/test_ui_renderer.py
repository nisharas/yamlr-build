from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


def test_render_welcome():
    """Verify welcome screen rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_welcome("/tmp", "1.30")
        mock_print.assert_called()

def test_render_explain():
    """Verify explain panel rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_explain("concept", {"title": "Title", "definition": "Def"})
        mock_print.assert_called()

def test_render_summary():
    """Verify summary table rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_summary({"total_files": 1, "verified": 1})
        mock_print.assert_called()

def test_render_batch_summary():
    """Verify batch summary rendering."""
    mock_report = MagicMock()
    mock_report.results = [MagicMock(violations=[], integrity_violations=[])]
    mock_report.total_files = 1
    mock_report.total_time_ms = 100
    
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_batch_summary(mock_report, False)
        mock_print.assert_called()

def test_render_score_animation():
    """Verify score animation rendering."""
    mock_report = MagicMock()
    mock_report.results = [MagicMock(health_score=95.0)]
    
    with patch('yamlr.ui.theme.console.print') as mock_print:
        with patch('time.sleep'):
            RichRenderer.render_score_animation(mock_report)
            mock_print.assert_called()

def test_render_integrity_ring():
    """Verify integrity ring rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_integrity_ring(95.0)
        mock_print.assert_called()

def test_render_breadcrumb():
    """Verify breadcrumb rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_breadcrumb("scan")
        mock_print.assert_called()
