from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import run_standalone


def test_cli_admin_stats():
    """Verify admin stats dispatch."""
    with patch('sys.argv', ['yamlr', 'admin', 'stats']):
        with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
            with patch('yamlr.ui.theme.console.print') as mock_print:
                run_standalone()
                assert any("Engine Diagnostics" in str(call) or "License Tier" in str(call) for call in mock_print.call_args_list)

def test_cli_admin_health():
    """Verify admin health dispatch."""
    with patch('sys.argv', ['yamlr', 'admin', 'health']):
        with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
            with patch('yamlr.ui.theme.console.print') as mock_print:
                run_standalone()
                assert any("Licensing Gateway" in str(call) for call in mock_print.call_args_list)
