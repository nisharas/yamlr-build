import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import cmd_version


def test_cmd_version_basic():
    """Verify basic version command output."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        cmd_version()
        assert any("Yamlr" in str(call) for call in mock_print.call_args_list)

def test_cmd_version_with_native_info():
    """Verify version command with native build info."""
    mock_native = MagicMock()
    mock_native.native_get_build_info.return_value = "Native-Core-v1"
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        with patch('yamlr.core_logic.console.print') as mock_print:
            cmd_version()
            assert any("Native-Core-v1" in str(call) for call in mock_print.call_args_list)
