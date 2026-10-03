from unittest.mock import MagicMock, patch

import pytest

from yamlr.ui.renderer import RichRenderer


def test_render_technical_dossier():
    """Verify technical dossier rendering."""
    data = {
        "title": "Test Concept",
        "definition": "A test definition.",
        "rationale": "Why we do this.",
        "impact": "High ROI",
        "example": "test: example"
    }
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_technical_dossier("test", data)
        mock_print.assert_called()
        panel = mock_print.call_args[0][0]
        assert "Yamlr Technical Authority" in str(panel.title)
