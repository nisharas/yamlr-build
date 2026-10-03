from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import run_standalone


def test_cli_help_all():
    """Verify help --all dispatch."""
    with patch('sys.argv', ['yamlr', 'help', '--all']):
        with patch('yamlr.cli.parser.create_parser') as mock_parser:
            mock_parser.return_value.parse_known_args.return_value = (MagicMock(command="help", all=True), [])
            with patch('yamlr.cli.main._render_global_help') as mock_render:
                run_standalone()
                mock_render.assert_called_with(True)

def test_cli_help_topic():
    """Verify help <topic> dispatch."""
    with patch('sys.argv', ['yamlr', 'help', 'scan']):
        with patch('yamlr.cli.handlers._handle_help_alias') as mock_handle:
            run_standalone()
            mock_handle.assert_called_once()
