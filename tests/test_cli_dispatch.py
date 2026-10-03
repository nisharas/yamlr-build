import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import _dispatch_command


def test_dispatch_pro_gate():
    """Verify pro gate for premium commands."""
    args = MagicMock(command="dna")
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=False):
        with patch('yamlr.cli.main.console.print') as mock_print:
            with pytest.raises(SystemExit):
                _dispatch_command(args)
            assert any("Access Denied" in str(call) for call in mock_print.call_args_list)

def test_dispatch_invalid_command():
    """Verify error handling for invalid command dispatch."""
    args = MagicMock(command="invalid_cmd", k8s_version="1.30")
    with patch('yamlr.cli.main.console.print') as mock_print:
        with pytest.raises(SystemExit):
            _dispatch_command(args)
        assert any("Unknown command" in str(call) for call in mock_print.call_args_list)
