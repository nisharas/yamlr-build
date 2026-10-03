"""Unit tests for LSP Code Action provider and rule URLs."""
import json

import pytest

from yamlr.lsp import LspServer


def test_lsp_server_capabilities():
    server = LspServer()
    # Mock send_response to capture output
    captured = []
    server.send_response = lambda req_id, result: captured.append((req_id, result))

    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    server.handle_request(init_req)
    assert len(captured) == 1
    req_id, result = captured[0]
    assert req_id == 1
    assert result["capabilities"]["codeActionProvider"] is True


def test_lsp_code_action_generation(tmp_path):
    server = LspServer()
    captured = []
    server.send_response = lambda req_id, result: captured.append((req_id, result))

    broken_manifest = tmp_path / "broken.yaml"
    broken_manifest.write_text("""apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: test-deploy
spec:
  template:
    spec:
      containers:
      - name: web
        image: nginx:latest
""", encoding="utf-8")

    ca_req = {
        "jsonrpc": "2.0",
        "id": 42,
        "method": "textDocument/codeAction",
        "params": {
            "textDocument": {"uri": f"file:///{broken_manifest.as_posix()}"},
            "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}}
        }
    }
    server.handle_request(ca_req)
    assert len(captured) == 1
    req_id, actions = captured[0]
    assert req_id == 42
    assert len(actions) >= 1
    assert "Yamlr: Auto-repair manifest" in actions[0]["title"]
    assert actions[0]["kind"] == "quickfix"
