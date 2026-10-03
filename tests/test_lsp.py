import io
import json
from unittest.mock import MagicMock, patch

import pytest

from yamlr.lsp import LspServer


def test_lsp_handle_initialize():
    """Verify that LSP server handles initialize request."""
    server = LspServer()
    server.send_message = MagicMock()
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    
    server.handle_request(request)
    
    server.send_message.assert_called_once()
    response = server.send_message.call_args[0][0]
    assert response['id'] == 1
    assert "capabilities" in response['result']

def test_lsp_send_diagnostics():
    """Verify that LSP server sends diagnostics for a file."""
    server = LspServer()
    server.send_message = MagicMock()
    
    # Mock violation
    v = MagicMock()
    v.rule_id = "Y-001"
    v.severity = "CRITICAL"
    v.message = "Test"
    v.line_no = 5
    
    # Mock result
    res = MagicMock()
    res.integrity_violations = [v]
    
    with patch('yamlr.lsp.streaming_scan', return_value=[res]):
        server.send_diagnostics("file:///test.yaml", "/test.yaml")
        
    server.send_message.assert_called()
    notification = server.send_message.call_args[0][0]
    assert notification['method'] == "textDocument/publishDiagnostics"
    assert len(notification['params']['diagnostics']) > 0
    diag = notification['params']['diagnostics'][0]
    assert diag['code'] == "Y-001"
    assert diag['range']['start']['line'] == 4
