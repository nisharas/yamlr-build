from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.handlers import _handle_help_alias
from yamlr.cli.main import run_standalone

def test_handle_help_alias():
    """Verify help alias logic."""
    args = MagicMock(topic=None)
    with patch('yamlr.cli.main._render_global_help') as mock_help:
        _handle_help_alias(args)
        mock_help.assert_called_once()

def test_handle_help_topic():
    """Verify help topic redirection."""
    args = MagicMock(topic="scan")
    with patch('argparse.ArgumentParser.parse_args') as mock_parse:
        _handle_help_alias(args)
        mock_parse.assert_called_once_with(["scan", "--help"])
