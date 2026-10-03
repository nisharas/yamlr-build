from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_dna


def test_cmd_dna_no_files(temp_workspace):
    """Verify DNA command handles directories with no YAML files."""
    with patch('yamlr.core.commands.console.print') as mock_print:
        cmd_dna(temp_workspace)
        assert any("No YAML files found" in str(call) for call in mock_print.call_args_list)

