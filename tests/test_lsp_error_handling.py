import sys
from unittest.mock import MagicMock, patch

import pytest

from yamlr.lsp import LspServer


def test_lsp_server_error_handling():
    """Verify LSP server handles scanning errors gracefully."""
    server = LspServer()
    # Mock send_diagnostics to fail
    with patch.object(server, 'send_diagnostics', side_effect=Exception("Crash")):
        with patch('sys.stderr.write') as mock_err:
            server.handle_request({"method": "textDocument/didOpen", "params": {"textDocument": {"uri": "file://test.yaml"}}})
            mock_err.assert_called()

def test_lsp_notification_crash_safety():
    """Verify that a crash in diagnostic generation doesn't kill the server."""
    server = LspServer()
    # Mock handle_request to fail
    with patch.object(server, 'send_diagnostics', side_effect=Exception("Crash")):
        # Call handler - should be caught by try-except in handle_request
        server.handle_request({"method": "textDocument/didOpen", "params": {"textDocument": {"uri": "file://test.yaml"}}})
        # No exception should be raised
