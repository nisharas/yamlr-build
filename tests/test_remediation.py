import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import _apply_atomic_fix, apply_remediation, render_resource_results


def test_apply_atomic_fix_success(temp_workspace):
    """Verify atomic fix application with backup."""
    fpath = os.path.join(temp_workspace, "test.yaml")
    with open(fpath, 'w') as f: f.write("content")
    
    res = MagicMock(file_path=fpath)
    fix = MagicMock(field_path="spec.replicas", suggested_value="3")
    telemetry = MagicMock()
    
    with patch('yamlr_native.native_record_telemetry'):
        with patch('yamlr_native.native_apply_fix_atomic', return_value=True):
            with patch('yamlr.ui.theme.console.print'):
                _apply_atomic_fix(res, fix, telemetry)
            
    assert os.path.exists(fpath + ".bak")

@patch('sys.stdin.isatty', return_value=False)
@patch('yamlr.cli.remediation._apply_atomic_fix')
def test_apply_remediation_cicd(mock_fix, mock_tty):
    """Verify CI/CD remediation auto-apply."""
    res = MagicMock(file_path="test.yaml")
    fix = MagicMock(field_path="spec", message="Fix it")
    res.suggested_fixes = [fix]
    
    # Mode: apply=True
    apply_remediation(res, MagicMock(), apply=True)
    mock_fix.assert_called_once()

@patch('sys.stdin.isatty', return_value=True)
@patch('yamlr.cli.remediation.console.input', return_value='y')
@patch('yamlr.cli.remediation._apply_atomic_fix')
def test_apply_remediation_interactive(mock_fix, mock_input, mock_tty):
    """Verify interactive remediation."""
    res = MagicMock(file_path="test.yaml")
    fix = MagicMock(field_path="spec", message="Fix it")
    res.suggested_fixes = [fix]
    
    apply_remediation(res, MagicMock(), apply=False)
    mock_fix.assert_called_once()

@patch('yamlr.ui.theme.console.print')
def test_render_resource_results(mock_print):
    """Verify per-resource rendering."""
    res = MagicMock()
    res.violations = [MagicMock(field_path="v1", message="m1")]
    res.health_score = 80.0
    res.identity = MagicMock(kind="Pod", name="p1")
    res.suggested_fixes = []
    
    render_resource_results(res, MagicMock(), "scan", False)
    mock_print.assert_called()

import os
