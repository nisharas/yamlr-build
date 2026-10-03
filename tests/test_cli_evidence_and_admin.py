import json
import os
import tarfile
from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.handlers import _cmd_admin, cmd_doctor, cmd_evidence, cmd_init
from yamlr.cli.main import run_standalone
from yamlr.core_logic import _record_healing_impact_local, cmd_roi, cmd_secure


def test_cmd_evidence(temp_workspace):
    config = os.path.join(temp_workspace, ".yamlr.yaml")
    base = os.path.join(temp_workspace, ".yamlr-baseline")
    with open(config, "w") as f: f.write("config")
    with open(base, "w") as f: f.write("base")
    
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        cmd_evidence(temp_workspace)
        assert mock_print.called
        
        # Verify tar created
        tar_files = [f for f in os.listdir(".") if f.endswith(".tar.gz")]
        if tar_files:
            os.remove(tar_files[0])

def test_cmd_evidence_error(temp_workspace):
    with patch('tarfile.open', side_effect=Exception("tar error")):
        with patch('yamlr.cli.handlers.console.print') as mock_print:
            cmd_evidence(temp_workspace)
            assert any("Evidence packaging failed" in str(call) for call in mock_print.call_args_list)

def test_cmd_init_success(temp_workspace):
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        cmd_init(temp_workspace)
        assert os.path.exists(os.path.join(temp_workspace, ".yamlr.yaml"))
        assert os.path.exists(os.path.join(temp_workspace, ".yamlr-baseline"))

def test_cmd_init_already_exists(temp_workspace):
    config = os.path.join(temp_workspace, ".yamlr.yaml")
    with open(config, "w") as f: f.write("config")
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        cmd_init(temp_workspace)
        assert any("already initialized" in str(call) for call in mock_print.call_args_list)

def test_cmd_init_error():
    with patch('os.makedirs', side_effect=Exception("dir error")):
        with patch('yamlr.cli.handlers.console.print') as mock_print:
            cmd_init("/invalid/path/123")
            assert any("Initialization failed" in str(call) for call in mock_print.call_args_list)

def test_cmd_admin_subcommands():
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        _cmd_admin("health")
        assert any("Licensing Gateway" in str(call) for call in mock_print.call_args_list)
        _cmd_admin("users")
        assert any("Latest Activation" in str(call) for call in mock_print.call_args_list)

def test_cmd_admin_stats():
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        _cmd_admin("stats")
        assert any("Machine ID" in str(call) or "License Tier" in str(call) for call in mock_print.call_args_list)

def test_cmd_admin_stats_error():
    with patch('yamlr.cli.handlers.console.print') as mock_print:
        _cmd_admin("unknown_sub")
        assert any("Engine Diagnostics" in str(call) for call in mock_print.call_args_list)

def test_cmd_doctor_all():
    with patch('yamlr_native.native_get_build_info', return_value={"version": "1.0"}):
        with patch('shutil.which', return_value=True):
            with patch('yamlr.cli.handlers.console.print') as mock_print:
                assert cmd_doctor() is True

def test_cmd_doctor_error():
    with patch('yamlr_native.native_get_build_info', side_effect=Exception("err")):
        with patch('shutil.which', return_value=False):
            with patch('yamlr.cli.handlers.console.print') as mock_print:
                assert cmd_doctor() is True

@patch('yamlr.core.commands._discover_manifests')
def test_cmd_roi_logic(mock_discover):
    mock_discover.return_value = ["test.yaml"]
    
    with patch('builtins.open', MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "content"
        with patch('yamlr_native.native_shard', return_value=["shard"]):
            mock_manifest = MagicMock()
            mock_manifest.integrity_violations = [MagicMock(check_name="Y-101")]
            with patch('yamlr_native.native_structurize', return_value=mock_manifest):
                with patch('yamlr.core.commands.console.print') as mock_print:
                    res = cmd_roi(".")
                    assert res["manifests_analyzed"] == 1
                    assert any("Impact Analysis" in str(call) for call in mock_print.call_args_list)

def test_record_healing_impact_local():
    telemetry = MagicMock(toil_mitigated=0)
    _record_healing_impact_local(telemetry, "Y-101")
    assert telemetry.toil_mitigated == 1

@patch('yamlr_native.native_discover_resources')
def test_cmd_secure_logic(mock_discover):
    mock_svc = MagicMock(kind="Service", namespace="def", selector={"app":"web"}, ports=[80])
    mock_svc.name = "app"
    mock_res = MagicMock(identity=mock_svc)
    mock_discover.return_value = [mock_res]
    
    with patch('yamlr.core_logic.console.print') as mock_print:
        cmd_secure(".")
        assert any("Suggested Policy for app" in str(call) for call in mock_print.call_args_list)

def test_run_standalone_no_args():
    with patch('sys.argv', ['yamlr']):
        with patch('yamlr.core_logic.cmd_welcome') as mock_welcome:
            run_standalone()
            mock_welcome.assert_called_once()
