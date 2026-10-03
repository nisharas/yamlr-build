import os
from unittest.mock import MagicMock, patch
import pytest

from yamlr.cli.handlers import _cmd_install, _cmd_update, _cmd_version, cmd_doctor, cmd_restore


def test_cmd_install_invalid():
    """Verify install command with invalid target."""
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        _cmd_install("invalid")
        mock_print.assert_called_once()

@patch('yamlr.core.backups.BackupManager.restore_last_session')
def test_cmd_restore(mock_restore):
    """Verify restore command."""
    cmd_restore(".")
    mock_restore.assert_called_once()

def test_cmd_version():
    """Verify version command."""
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        _cmd_version()
        mock_print.assert_called()

def test_cmd_update():
    """Verify update command."""
    _cmd_update()

@patch('yamlr_native.native_get_build_info', return_value={"version": "0.1.0"})
def test_cmd_doctor(mock_build):
    """Verify doctor command."""
    cmd_doctor()

