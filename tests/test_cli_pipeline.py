import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import _execute_scan_heal_pipeline


@patch('yamlr_native.native_discover_resources')
@patch('yamlr_native.native_build_topology_graph')
@patch('yamlr.ui.renderer.RichRenderer.render_graph')
def test_execute_pipeline_graph(mock_render, mock_graph, mock_discover):
    """Verify graph command execution."""
    args = MagicMock(command="graph", path=".", focus=None)
    mock_discover.return_value = []
    mock_graph.return_value = []
    
    _execute_scan_heal_pipeline(args)
    mock_render.assert_called_once()

@patch('yamlr.cli.pipeline.initialize_engine')
@patch('yamlr.cli.pipeline.execute_pipeline')
@patch('yamlr.cli.pipeline.render_report')
def test_execute_pipeline_scan(mock_render, mock_exec, mock_init):
    """Verify scan command execution."""
    args = MagicMock(command="scan", path=".", k8s_version=None, push_telemetry=False)
    mock_init.return_value = []
    mock_exec.return_value = MagicMock()
    
    _execute_scan_heal_pipeline(args)
    mock_render.assert_called_once()

@patch('yamlr.cli.pipeline.initialize_engine')
@patch('yamlr.cli.pipeline.ingest_crds')
def test_execute_pipeline_with_crd(mock_ingest, mock_init):
    """Verify CRD ingestion in pipeline."""
    args = MagicMock(command="scan", path=".", k8s_version="1.30", crd="crd.yaml", push_telemetry=False)
    with patch('yamlr.cli.pipeline.execute_pipeline'):
        with patch('yamlr.cli.pipeline.render_report'):
            _execute_scan_heal_pipeline(args)
            mock_ingest.assert_called_once()
