from unittest.mock import MagicMock, patch

import pytest

from yamlr.integrations import cmd_install_hook


def test_install_hook_fail():
    """Verify install hook failure handling."""
    with patch('os.path.exists', return_value=False):
        with patch('yamlr.ui.theme.console.print') as mock_print:
            cmd_install_hook()
            # Check for ERROR in the output
            found = False
            for call in mock_print.call_args_list:
                if "ERROR" in str(call[0]):
                    found = True
                    break
            assert found
