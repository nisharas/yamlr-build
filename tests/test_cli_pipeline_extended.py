import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import _execute_scan_heal_pipeline


@patch('yamlr.cli.pipeline.execute_pipeline')
@patch('yamlr.cli.pipeline.render_report')
def test_execute_scan_heal_pipeline(mock_render, mock_pipeline, temp_workspace):
    """Verify scan/heal pipeline execution and rendering."""
    args = MagicMock(path=temp_workspace, command="scan", k8s_version="1.30", output=None)
    
    mock_report = MagicMock()
    mock_report.results = []
    mock_report.total_files = 0
    mock_pipeline.return_value = mock_report
    
    with patch('yamlr.cli.pipeline.initialize_engine', return_value=[]):
        _execute_scan_heal_pipeline(args)
        mock_pipeline.assert_called_once()
        mock_render.assert_called_once()
