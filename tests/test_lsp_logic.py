import io
import json
from unittest.mock import MagicMock, patch

import pytest

from yamlr.lsp import LspServer, cmd_lsp


def test_lsp_initialize():
    """Verify LSP initialization response."""
    server = LspServer()
    payload = b'{"jsonrpc": "2.0", "id": 1, "method": "initialize"}'
    content = b'Content-Length: ' + str(len(payload)).encode() + b'\r\n\r\n' + payload
    server.reader = io.BytesIO(content)
    server.writer = io.BytesIO()
    
    # Run one iteration (hacky but works for unit test)
    try:
        server.run()
    except EOFError:
        pass
    except Exception:
        pass # readline will fail eventually
    
    output = server.writer.getvalue().decode('utf-8')
    assert "capabilities" in output
    assert "diagnosticProvider" in output

@patch('yamlr.lsp.streaming_scan')
def test_lsp_diagnostics(mock_scan):
    """Verify LSP diagnostics notification."""
    server = LspServer()
    server.writer = io.BytesIO()
    
    violation = MagicMock(line_no=10, severity="CRITICAL", rule_id="ERR-01", message="Test failure")
    mock_scan.return_value = [MagicMock(integrity_violations=[violation])]
    
    server.send_diagnostics("file://test.yaml", "test.yaml")
    
    output = server.writer.getvalue().decode('utf-8')
    assert "textDocument/publishDiagnostics" in output
    assert "Test failure" in output
    assert "ERR-01" in output
