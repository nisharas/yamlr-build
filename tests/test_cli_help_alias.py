from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.handlers import _handle_help_alias

def test_handle_help_alias_topic():
    """Verify help alias with topic."""
    args = MagicMock(topic="scan")
    with patch('yamlr.cli.parser.create_parser') as mock_parser_factory:
        mock_parser = MagicMock()
        mock_parser_factory.return_value = mock_parser
        # parse_args([topic, '--help']) should raise SystemExit(0)
        mock_parser.parse_args.side_effect = SystemExit(0)
        
        _handle_help_alias(args)
        mock_parser.parse_args.assert_called_with(["scan", "--help"])

def test_handle_help_alias_global():
    """Verify global help rendering."""
    args = MagicMock(topic=None, all=False)
    with patch('yamlr.cli.main._render_global_help') as mock_render:
        _handle_help_alias(args)
        mock_render.assert_called_with(False)
