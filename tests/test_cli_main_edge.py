import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.main import (
    _dispatch_command,
    _export_json_report,
    _handle_exit_code,
    detect_version,
    ingest_crds,
    initialize_engine,
    main,
)


def test_detect_version_env():
    """Verify version detection from environment variable."""
    with patch.dict(os.environ, {"YAMLR_K8S_VERSION": "1.32"}):
        assert detect_version() == "1.32"

def test_detect_version_kubectl_fail():
    """Verify version detection fallback when kubectl fails."""
    with patch('subprocess.run', side_effect=Exception("fail")):
        assert detect_version() == "1.30"

def test_initialize_engine_fail():
    """Verify engine initialization failure exits."""
    with patch('yamlr_native.native_get_schema_for_version', side_effect=Exception("fail")):
        with pytest.raises(SystemExit) as e:
            initialize_engine("1.30")
        assert e.value.code == 1

def test_ingest_crds_fail():
    """Verify CRD ingestion failure exits."""
    with patch('builtins.open', side_effect=Exception("fail")):
        with pytest.raises(SystemExit) as e:
            ingest_crds("path", [])
        assert e.value.code == 1

def test_handle_exit_code_levels():
    """Verify exit code handling for different severity levels."""
    report = MagicMock()
    res = MagicMock()
    v = MagicMock(severity="ERROR")
    res.violations = [v]
    res.integrity_violations = []
    report.results = [res]
    
    with pytest.raises(SystemExit) as e:
        _handle_exit_code(report, "error")
    assert e.value.code == 1
    
    # Test with note level
    v.severity = "NOTE"
    with pytest.raises(SystemExit) as e:
        _handle_exit_code(report, "note")
    assert e.value.code == 1

def test_export_json_report(temp_workspace):
    """Verify JSON report export."""
    output_file = os.path.join(temp_workspace, "report.json")
    report = MagicMock()
    report.total_files = 1
    report.total_time_ms = 100
    res = MagicMock(file_path="test.yaml", health_score=100.0)
    res.violations = [MagicMock(field_path="f1", message="m1", severity="ERROR")]
    res.integrity_violations = [MagicMock(check_name="c1", message="m2", severity="WARNING")]
    report.results = [res]
    
    _export_json_report(report, output_file)
    assert os.path.exists(output_file)
    with open(output_file, 'r') as f:
        data = json.load(f)
        assert data["results"][0]["file"] == "test.yaml"

def test_dispatch_command_various():
    """Verify dispatch for various commands."""
    # Explain
    args = MagicMock(command="explain", path=".", flag=None)
    with patch('yamlr.core_logic.cmd_explain_universal') as mock_explain:
        _dispatch_command(args)
        mock_explain.assert_called_once()
    
    # Graph/Scan/Heal pipeline
    args = MagicMock(command="scan", path=".", fail_on=None)
    with patch('yamlr.cli.main._execute_scan_heal_pipeline') as mock_pipeline:
        _dispatch_command(args)
        mock_pipeline.assert_called_once()

def test_main_version():
    """Verify main entry with --version."""
    with patch('sys.argv', ['yamlr', '--version']):
        with patch('yamlr.core_logic.cmd_version') as mock_version:
            main()
            mock_version.assert_called_once()

def test_main_empty():
    """Verify main entry with no args."""
    with patch('sys.argv', ['yamlr']):
        with patch('yamlr.core_logic.cmd_welcome') as mock_welcome:
            main()
            mock_welcome.assert_called_once()
