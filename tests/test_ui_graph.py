from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


def test_render_graph():
    """Verify topology graph rendering."""
    mock_edge = MagicMock()
    mock_edge.source = "Service/my-svc"
    mock_edge.target = "Deployment/my-app"
    mock_edge.edge_type = "selector"
    
    mock_blast = MagicMock()
    mock_blast.source = "Service/my-svc"
    mock_blast.affected_count = 1
    mock_blast.depth = 1
    mock_blast.risk_level = "HIGH"
    
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_graph([mock_edge], mock_blast)
        mock_print.assert_called()
        # Verify specific content
        calls = str(mock_print.call_args_list)
        assert "Yamlr Topology Graph" in calls
        assert "Blast Radius" in calls
