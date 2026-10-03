import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import (
    cmd_completion,
    cmd_dna,
    cmd_explain_universal,
    cmd_fleet,
    cmd_pulse,
    cmd_roi,
    cmd_rollback,
    cmd_secure,
)


@patch('yamlr_native.native_discover_resources', return_value=[])
@patch('yamlr.ui.theme.console.print')
def test_cmd_pulse_no_files(mock_print, mock_discover):
    cmd_pulse(".")
    assert mock_print.called

@patch('yamlr_native.native_discover_resources', return_value=[MagicMock(identity=MagicMock(kind="Pod", name="test"))])
@patch('yamlr_native.native_shard', return_value=["shard"])
@patch('yamlr_native.native_structurize', return_value=MagicMock(integrity_violations=[]))
@patch('yamlr.ui.theme.console.print')
def test_cmd_pulse_success(mock_print, mock_struct, mock_shard, mock_discover):
    cmd_pulse(".")
    assert any("Live Pulse" in str(call) for call in mock_print.call_args_list)

@patch('yamlr_native.native_discover_resources', return_value=[])
@patch('yamlr.ui.theme.console.print')
def test_cmd_secure_no_files(mock_print, mock_discover):
    cmd_secure(".")
    assert mock_print.called

@patch('yamlr.core.backups.BackupManager')
@patch('yamlr.ui.theme.console.print')
def test_cmd_rollback(mock_print, mock_bm):
    cmd_rollback(".")
    mock_bm.return_value.restore_last_session.assert_called_once()

@patch('yamlr.ui.theme.console.print')
def test_cmd_fleet(mock_print):
    cmd_fleet()
    assert mock_print.called

@patch('yamlr.ui.theme.console.print')
def test_cmd_completion(mock_print):
    cmd_completion("zsh")
    assert any("zsh" in str(call) for call in mock_print.call_args_list)
    cmd_completion("bash")
    assert any("bash" in str(call) for call in mock_print.call_args_list)
    cmd_completion("fish")
    assert any("fish" in str(call) for call in mock_print.call_args_list)

@patch('yamlr.ui.theme.console.print')
def test_cmd_explain_universal(mock_print):
    cmd_explain_universal("registry")
    assert mock_print.called
