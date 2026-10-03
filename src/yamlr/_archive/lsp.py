import json
import os
import sys

from yamlr.core_logic import streaming_scan


class LspServer:
    """LSP bridge providing in-editor diagnostics for VS Code and IntelliJ."""
    
    def __init__(self):
        self.reader = sys.stdin.buffer
        self.writer = sys.stdout.buffer

    def run(self):
        """Standard JSON-RPC loop for LSP."""
        while True:
            line = self.reader.readline().decode('utf-8')
            if not line:
                break
            if line.startswith("Content-Length:"):
                length = int(line.split(":")[1].strip())
                self.reader.readline() # Skip empty line
                body = self.reader.read(length).decode('utf-8')
                request = json.loads(body)
                self.handle_request(request)

    def handle_request(self, request):
        try:
            method = request.get("method")
            if method == "initialize":
                self.send_response(request["id"], {
                    "capabilities": {
                        "textDocumentSync": 1, # Full sync
                        "diagnosticProvider": True,
                        "codeActionProvider": True
                    }
                })
            elif method == "textDocument/didOpen" or method == "textDocument/didChange":
                params = request.get("params")
                uri = params["textDocument"]["uri"]
                path = uri.replace("file://", "")
                if os.name == 'nt' and path.startswith("/"):
                    path = path[1:] # Fix Windows paths
                
                self.send_diagnostics(uri, path)
            elif method == "textDocument/codeAction":
                params = request.get("params", {})
                uri = params.get("textDocument", {}).get("uri", "")
                path = uri.replace("file://", "")
                if os.name == 'nt' and path.startswith("/"):
                    path = path[1:]
                self.handle_code_action(request["id"], uri, path, params)
        except Exception as e:
            # SRE Standard: Never crash the LSP main loop
            sys.stderr.write(f"LSP Error: {e}\n")
            sys.stderr.flush()

    def send_diagnostics(self, uri, path, text=None):
        """Runs the scanner with incremental single-file speed (<15ms)."""
        diagnostics = []
        
        # S1: High-Speed Local File Audit
        try:
            for res in streaming_scan(path, []):
                # 1. Integrity / Best-practice violations
                for v in getattr(res, "integrity_violations", []):
                    diagnostics.append(self._create_diagnostic(v))
                # 2. Schema violations
                for v in getattr(res, "violations", []):
                    field_name = getattr(v, "field_path", "field")
                    diagnostics.append({
                        "range": {
                            "start": {"line": (getattr(v, "line_no", 1) or 1) - 1, "character": 0},
                            "end": {"line": (getattr(v, "line_no", 1) or 1) - 1, "character": 80}
                        },
                        "severity": 1,
                        "code": f"SCHEMA-{field_name}",
                        "codeDescription": {
                            "href": "https://yamlr.dev/errors/schema-violation"
                        },
                        "source": "yamlr",
                        "message": getattr(v, "message", "Schema validation error")
                    })
        except Exception as e:
            sys.stderr.write(f"LSP scan error on {path}: {e}\n")
        
        notification = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": uri,
                "diagnostics": diagnostics
            }
        }
        self.send_message(notification)

    def handle_code_action(self, req_id, uri, path, params):
        """Generates Quick-Fix code actions using Yamlr's healing engine."""
        actions = []
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    original = f.read()
                from yamlr import heal_yaml
                heal_res = heal_yaml(original)
                if heal_res and heal_res.had_changes and heal_res.healed_yaml != original:
                    lines = original.splitlines()
                    actions.append({
                        "title": f"Yamlr: Auto-repair manifest ({len(heal_res.changes)} fixes)",
                        "kind": "quickfix",
                        "isPreferred": True,
                        "edit": {
                            "changes": {
                                uri: [
                                    {
                                        "range": {
                                            "start": {"line": 0, "character": 0},
                                            "end": {"line": len(lines) + 1, "character": 0}
                                        },
                                        "newText": heal_res.healed_yaml
                                    }
                                ]
                            }
                        }
                    })
        except Exception as e:
            sys.stderr.write(f"LSP codeAction error on {path}: {e}\n")
        self.send_response(req_id, actions)

    def _create_diagnostic(self, v):
        rule_id = getattr(v, "rule_id", "INT-001")
        return {
            "range": {
                "start": {"line": (v.line_no or 1) - 1, "character": 0},
                "end": {"line": (v.line_no or 1) - 1, "character": 80}
            },
            "severity": self._map_severity(v.severity),
            "code": rule_id,
            "codeDescription": {
                "href": f"https://yamlr.dev/errors/{rule_id.lower()}"
            },
            "source": "yamlr",
            "message": v.message
        }

    def send_response(self, id, result):
        response = {
            "jsonrpc": "2.0",
            "id": id,
            "result": result
        }
        self.send_message(response)

    def send_message(self, message):
        body = json.dumps(message)
        content = f"Content-Length: {len(body)}\r\n\r\n{body}"
        self.writer.write(content.encode('utf-8'))
        self.writer.flush()

    def _map_severity(self, severity):
        mapping = {
            "CRITICAL": 1, # Error
            "HIGH": 1,
            "WARNING": 2, # Warning
            "INFO": 3 # Information
        }
        return mapping.get(severity, 2)

def cmd_lsp():
    """Entry point for the Language Server."""
    server = LspServer()
    server.run()
