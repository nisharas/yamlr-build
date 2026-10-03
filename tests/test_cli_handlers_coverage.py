from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.handlers import (
    _cmd_install,
    _cmd_update,
    _cmd_upgrade,
    _cmd_version,
    cmd_restore,
    handle_informational_commands,
)


def test_cmd_update():
    """Verify _cmd_update."""
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        with patch('time.sleep'):
            _cmd_update()
            assert mock_print.call_count >= 2

def test_cmd_upgrade():
    """Verify _cmd_upgrade."""
    with patch('webbrowser.open') as mock_open:
        _cmd_upgrade()
        mock_open.assert_called_once_with("https://yamlr.dev/pro")

def test_cmd_install_hook():
    """Verify _cmd_install hook."""
    with patch('yamlr.integrations.cmd_install_hook') as mock_hook:
        _cmd_install("hook")
        mock_hook.assert_called_once()

def test_cmd_install_action():
    """Verify _cmd_install action."""
    with patch('yamlr.integrations.cmd_install_action') as mock_action:
        _cmd_install("action")
        mock_action.assert_called_once()

def test_cmd_restore():
    """Verify cmd_restore."""
    with patch('yamlr.core.backups.BackupManager') as mock_bm:
        cmd_restore(".")
        mock_bm.return_value.restore_last_session.assert_called_once()

def test_cmd_version_coverage():
    """Verify _cmd_version."""
    with patch('yamlr.core_logic.cmd_version') as mock_v:
        _cmd_version()
        mock_v.assert_called_once()

def test_informational_commands_dispatch():
    """Verify informational commands routing."""
    # Test 'init'
    args = MagicMock(command="init", path=".")
    with patch('yamlr.cli.handlers.cmd_init') as mock_init:
        assert handle_informational_commands(args) is True
        mock_init.assert_called_once_with(".")
        
    # Test 'pulse'
    args = MagicMock(command="pulse", path=".")
    with patch('yamlr.core_logic.cmd_pulse') as mock_pulse:
        assert handle_informational_commands(args) is True
        mock_pulse.assert_called_once_with(".")
        
    # Test 'secure'
    args = MagicMock(command="secure", path=".")
    with patch('yamlr.cli.handlers.is_experimental_enabled', return_value=True):
        with patch('yamlr.core_logic.cmd_secure') as mock_secure:
            assert handle_informational_commands(args) is True
            mock_secure.assert_called_once_with(".")

    # Test 'mcp'
    args = MagicMock(command="mcp")
    with patch('yamlr.cli.handlers.cmd_mcp') as mock_mcp:
        assert handle_informational_commands(args) is True
        mock_mcp.assert_called_once()
        
    # Test 'evidence'
    args = MagicMock(command="evidence", path=".")
    with patch('yamlr.cli.handlers.cmd_evidence') as mock_ev:
        assert handle_informational_commands(args) is True
        mock_ev.assert_called_once_with(".")
        
    # Test 'completion'
    args = MagicMock(command="completion", shell="zsh")
    with patch('yamlr.core_logic.cmd_completion') as mock_comp:
        assert handle_informational_commands(args) is True
        mock_comp.assert_called_once_with("zsh")
