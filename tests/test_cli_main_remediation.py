import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import (
    _apply_atomic_fix,
    _handle_cicd_remediation,
    _handle_interactive_remediation,
    apply_remediation,
    render_resource_results,
)


def test_apply_remediation_interactive_yes():
    """Verify interactive remediation with 'y' input."""
    res = MagicMock()
    res.suggested_fixes = [MagicMock(field_path="spec", message="Fix it")]
    telemetry = MagicMock()
    
    with patch('sys.stdin.isatty', return_value=True):
        with patch('yamlr.cli.remediation.console.input', return_value='y'):
            with patch('yamlr.cli.remediation._apply_atomic_fix') as mock_fix:
                apply_remediation(res, telemetry, apply=False)
                mock_fix.assert_called_once()

def test_apply_remediation_interactive_no():
    """Verify interactive remediation with 'n' input."""
    res = MagicMock()
    res.suggested_fixes = [MagicMock(field_path="spec", message="Fix it")]
    telemetry = MagicMock()
    
    with patch('sys.stdin.isatty', return_value=True):
        with patch('yamlr.cli.remediation.console.input', return_value='n'):
            with patch('yamlr.cli.remediation._apply_atomic_fix') as mock_fix:
                apply_remediation(res, telemetry, apply=False)
                mock_fix.assert_not_called()

def test_handle_cicd_remediation_fail():
    """Verify CI/CD safety gate failure."""
    res = MagicMock(file_path="test.yaml")
    fix = MagicMock(field_path="spec")
    with pytest.raises(SystemExit) as e:
        _handle_cicd_remediation(res, fix, apply=False)
    assert e.value.code == 1

def test_apply_atomic_fix_error():
    """Verify error handling in atomic fix."""
    res = MagicMock(file_path="missing.yaml")
    fix = MagicMock()
    with patch('shutil.copy2', side_effect=Exception("File error")):
        with pytest.raises(SystemExit) as e:
            _apply_atomic_fix(res, fix, MagicMock())
        assert e.value.code == 1

def test_render_resource_results_heal(temp_workspace):
    """Verify result rendering with heal trigger."""
    res = MagicMock()
    res.violations = [MagicMock(field_path="v1", message="m1")]
    res.integrity_violations = []
    res.health_score = 80.0
    res.identity = None
    fpath = os.path.join(temp_workspace, "test.yaml")
    with open(fpath, "w") as f: f.write("content")
    res.file_path = fpath
    res.suggested_fixes = [MagicMock()]
    
    with patch('yamlr.cli.formatters.apply_remediation') as mock_remed:
        render_resource_results(res, MagicMock(), "heal", True)
        mock_remed.assert_called_once()
