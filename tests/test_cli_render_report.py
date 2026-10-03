import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import render_report


def test_render_report_with_results():
    """Verify render_report logic with findings."""
    mock_report = MagicMock()
    mock_report.results = [
        MagicMock(file_path="test.yaml", health_score=100, violations=[], integrity_violations=[], suggested_fixes=[])
    ]
    mock_report.total_files = 1
    mock_report.total_time_ms = 100
    
    mock_telemetry = MagicMock()
    
    with patch('yamlr_native.native_record_telemetry'):
        with patch('yamlr.cli.formatters._render_results_and_collisions') as mock_results:
            with patch('yamlr.cli.formatters._render_batch_summary'):
                with patch('yamlr.core_logic.audit_topology_outages'):
                    with patch('yamlr.cli.formatters._trigger_score_animation'):
                        render_report(mock_report, mock_telemetry, "scan", False)
                        mock_results.assert_called_once()
