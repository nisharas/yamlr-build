from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import apply_remediation


def test_apply_remediation_interactive():
    """Verify interactive remediation flow."""
    res = MagicMock()
    fix = MagicMock()
    fix.field_path = "spec.replicas"
    fix.message = "Low replicas"
    res.suggested_fixes = [fix]
    
    telemetry = MagicMock()
    
    with patch('sys.stdin.isatty', return_value=True):
        with patch('yamlr.cli.remediation._handle_interactive_remediation', return_value=True) as mock_handle:
            with patch('yamlr.cli.remediation._apply_atomic_fix') as mock_apply:
                apply_remediation(res, telemetry, True)
                mock_handle.assert_called_once()
                mock_apply.assert_called_once()

def test_apply_remediation_cicd():
    """Verify CI/CD remediation flow."""
    res = MagicMock()
    fix = MagicMock()
    res.suggested_fixes = [fix]
    telemetry = MagicMock()
    
    with patch('sys.stdin.isatty', return_value=False):
        with patch('yamlr.cli.remediation._handle_cicd_remediation') as mock_handle:
            with patch('yamlr.cli.remediation._apply_atomic_fix') as mock_apply:
                apply_remediation(res, telemetry, True)
                mock_handle.assert_called_once()
                mock_apply.assert_called_once()
