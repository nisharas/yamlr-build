from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


def test_render_k8s_field_dossier():
    """Verify K8s field dossier rendering."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_k8s_field_dossier("deployment.spec.replicas")
        mock_print.assert_called()
        panel = mock_print.call_args[0][0]
        assert "Native Registry Discovery" in str(panel.title)
