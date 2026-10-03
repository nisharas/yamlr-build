import io
import json
from unittest.mock import MagicMock, patch

import pytest

from yamlr.mcp_server import _execute_tool, run_mcp_server


def test_mcp_initialize():
    """Verify initialize request."""
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    with patch('sys.stdin', io.StringIO(json.dumps(req) + "\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            run_mcp_server()
            output = json.loads(mock_stdout.getvalue().strip())
            assert output["id"] == 1
            assert "serverInfo" in output["result"]

def test_mcp_tools_list():
    """Verify tools/list request."""
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    with patch('sys.stdin', io.StringIO(json.dumps(req) + "\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            run_mcp_server()
            output = json.loads(mock_stdout.getvalue().strip())
            assert output["id"] == 2
            assert len(output["result"]["tools"]) == 5

def test_mcp_tools_call():
    """Verify tools/call request."""
    req = {
        "jsonrpc": "2.0", 
        "id": 3, 
        "method": "tools/call", 
        "params": {"name": "scan_manifests", "arguments": {"path": "."}}
    }
    with patch('sys.stdin', io.StringIO(json.dumps(req) + "\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with patch('yamlr.mcp_server._execute_tool', return_value={"status": "success"}) as mock_exec:
                run_mcp_server()
                output = json.loads(mock_stdout.getvalue().strip())
                assert output["id"] == 3
                assert "content" in output["result"]
                mock_exec.assert_called_once_with("scan_manifests", {"path": "."})

def test_mcp_method_not_found():
    """Verify unknown method request."""
    req = {"jsonrpc": "2.0", "id": 4, "method": "unknown"}
    with patch('sys.stdin', io.StringIO(json.dumps(req) + "\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            run_mcp_server()
            output = json.loads(mock_stdout.getvalue().strip())
            assert output["error"]["code"] == -32601

def test_mcp_error_handling():
    """Verify exception handling during request parsing."""
    with patch('sys.stdin', io.StringIO("invalid json\n")):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            run_mcp_server()
            output = json.loads(mock_stdout.getvalue().strip())
            assert output["error"]["code"] == -32603

@patch('yamlr_native.NativeTelemetry')
@patch('yamlr_native.native_apply_fix_atomic', return_value=True)
def test_execute_tool_heal(mock_apply, mock_telemetry):
    """Verify _execute_tool heal logic."""
    with patch('yamlr.cli.main.detect_version', return_value="1.30"):
        with patch('yamlr.cli.main.initialize_engine', return_value=[]):
            mock_res = MagicMock(
                file_path="test.yaml", 
                health_score=80.0,
                violations=[MagicMock(field_path="v", message="msg")],
                integrity_violations=[MagicMock(check_name="i", message="msg")],
                suggested_fixes=[MagicMock(field_path="v", suggested_value="x")]
            )
            mock_report = MagicMock(results=[mock_res], total_files=1)
            with patch('yamlr.cli.main.execute_pipeline', return_value=mock_report):
                res = _execute_tool("heal_manifests", {"path": "."})
                assert res["status"] == "success"
                assert res["applied_fixes"] == 1
                assert len(res["results"]) == 1
                assert len(res["results"][0]["violations"]) == 2

def test_execute_tool_error():
    """Verify _execute_tool exception handling."""
    with patch('yamlr.cli.main.detect_version', side_effect=Exception("detect error")):
        res = _execute_tool("scan_manifests", {"path": "."})
        assert res["status"] == "error"
        assert res["message"] == "detect error"

@patch('yamlr_native.native_get_schema_info', create=True)
def test_execute_tool_get_openapi_schema(mock_schema):
    """Verify get_openapi_schema logic."""
    mock_schema.return_value = '{"openapi": "3.0.0"}'
    res = _execute_tool("get_openapi_schema", {"kind": "Deployment", "k8s_version": "1.30"})
    assert res["status"] == "success"
    assert "openapi" in res["schema"]
    mock_schema.assert_called_once_with("Deployment", "1.30")

def test_execute_tool_get_resource_dependencies():
    """Verify get_resource_dependencies logic."""
    with patch('yamlr.cli.main.detect_version', return_value="1.30"):
        with patch('yamlr.cli.main.initialize_engine', return_value=[]):
            mock_res1 = MagicMock()
            mock_res1.dependencies = [{"kind": "ConfigMap", "name": "app-config"}]
            mock_res1.identity.kind = "Deployment"
            mock_res1.identity.name = "web"
            
            mock_report = MagicMock(results=[mock_res1], total_files=1)
            with patch('yamlr.cli.main.execute_pipeline', return_value=mock_report):
                res = _execute_tool("get_resource_dependencies", {"path": ".", "kind": "ConfigMap", "name": "app-config"})
                assert res["status"] == "success"
                assert res["target"] == "ConfigMap/app-config"
                assert "Deployment web" in res["dependencies"]
