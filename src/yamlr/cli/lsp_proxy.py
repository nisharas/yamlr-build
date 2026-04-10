#!/usr/bin/env python3
"""
Yamlr Sovereign LSP Proxy (IP-Hardened)
--------------------------------------
Architecture:
- Protocol: LSP (Language Server Protocol)
- Logic: Thin Proxy. Delegates analysis to the native yamlr.exe.
- IP Protection: 🔒 High. The forensic engine is a compiled black-box.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

# 🛡️ MANDATORY: Late Imports to avoid crashing in environments without LSP stack
try:
    from lsprotocol.types import (
        TEXT_DOCUMENT_CODE_ACTION,
        TEXT_DOCUMENT_DID_CHANGE,
        TEXT_DOCUMENT_DID_OPEN,
        CodeAction,
        CodeActionKind,
        CodeActionParams,
        Command,
        Diagnostic,
        DiagnosticSeverity,
        DidChangeTextDocumentParams,
        DidOpenTextDocumentParams,
        Position,
        PublishDiagnosticsParams,
        Range,
    )
    from pygls.lsp.server import LanguageServer
    HAS_LSP_STACK = True
except ImportError:
    HAS_LSP_STACK = False

# Setup logging to stderr
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("yamlr.lsp_proxy")

class SovereignLspServer(LanguageServer if HAS_LSP_STACK else object):
    def __init__(self):
        if HAS_LSP_STACK:
            super().__init__("yamlr-lsp-proxy", "v1.1")
        self.binary_path = os.getenv("YAMLR_BINARY_PATH", "yamlr")
        self._diagnostics_cache: Dict[str, List[Any]] = {}

    def run_native_scan(self, content: str, source_path: str) -> Dict[str, Any]:
        """Invokes the native yamlr.exe as a subprocess to protect IP."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tf:
            tf.write(content)
            temp_path = tf.name

        try:
            cmd = [self.binary_path, "scan", temp_path, "--output", "json"]
            logger.info(f"🚀 Dispatching to Native Engine: {' '.join(cmd)}")
            
            # Execute with silenced logs to avoid polluting stderr if needed
            env = os.environ.copy()
            env["YAMLR_LOG_LEVEL"] = "ERROR"
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                env=env,
                check=False # We handle non-zero exits (violations) manually
            )
            
            if not result.stdout.strip():
                logger.error(f"Native engine returned empty stdout. Stderr: {result.stderr}")
                return {}

            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Failed to invoke native engine: {e}")
            return {}
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if HAS_LSP_STACK:
    proxy_server = SovereignLspServer()

    @proxy_server.feature(TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls: SovereignLspServer, params: DidOpenTextDocumentParams):
        analyze_and_publish(ls, params.text_document.uri)

    @proxy_server.feature(TEXT_DOCUMENT_DID_CHANGE)
    def did_change(ls: SovereignLspServer, params: DidChangeTextDocumentParams):
        analyze_and_publish(ls, params.text_document.uri)

    @proxy_server.feature(TEXT_DOCUMENT_CODE_ACTION)
    def code_action(ls: SovereignLspServer, params: CodeActionParams) -> List[CodeAction]:
        """Thin adapter for code actions."""
        actions = []
        uri = params.text_document.uri
        diagnostics = ls._diagnostics_cache.get(uri, [])
        for diag in diagnostics:
            if diag.range.start.line <= params.range.start.line <= diag.range.end.line:
                suggestion = diag.data.get("suggestion")
                if suggestion:
                    action = CodeAction(
                        title=f"Yamlr: {suggestion}",
                        kind=CodeActionKind.QuickFix,
                        diagnostics=[diag],
                        command=Command(title="Yamlr: Heal File", command="yamlr.healFile", arguments=[uri, diag.code]),
                    )
                    actions.append(action)
        return actions

def analyze_and_publish(ls: SovereignLspServer, uri: str):
    """Bridge Native subprocess findings to LSP Diagnostics."""
    try:
        path = unquote(uri.replace("file://", ""))
        if os.name == "nt":
            if path.startswith("/"): path = path[1:]
            path = path.replace("/", "\\")

        # Get document content from buffer
        doc = ls.workspace.get_text_document(uri)
        if not doc: return

        # 🚀 THE SOVEREIGN BOUNDARY: Run native engine
        raw_results = ls.run_native_scan(doc.source, path)
        
        diagnostics = []
        # Parse the 'results' field from our stable JSON API
        results_list = raw_results.get("results", [])
        if not results_list:
            logger.warning(f"No results returned for {path}")
            return

        findings = results_list[0].get("findings", [])
        for finding in findings:
            severity_str = (finding.get("severity") or "WARNING").upper()
            l_severity = DiagnosticSeverity.Warning
            if severity_str == "ERROR": l_severity = DiagnosticSeverity.Error
            elif severity_str == "INFO": l_severity = DiagnosticSeverity.Information

            line = (finding.get("line") or 1) - 1
            col = (finding.get("column") or 1) - 1
            
            rule_id = finding.get("rule_id", "yamlr")
            msg = finding.get("message", "Yamlr Finding")
            
            diag = Diagnostic(
                range=Range(start=Position(line=max(0, line), character=max(0, col)), 
                            end=Position(line=max(0, line), character=80)),
                message=f"yamlr: {rule_id}\n\n{msg}",
                severity=l_severity,
                source="yamlr",
                code=rule_id,
                data={"suggestion": finding.get("suggestion")},
            )
            diagnostics.append(diag)

        ls._diagnostics_cache[uri] = diagnostics
        ls.text_document_publish_diagnostics(PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics))
        logger.info(f"Published {len(diagnostics)} native diagnostics for {uri}")

    except Exception as e:
        logger.error(f"Sovereign Proxy Failure: {e}")

def start_lsp():
    """Proxy Entrypoint."""
    if not HAS_LSP_STACK:
        print("Error: LSP dependencies (pygls, lsprotocol) missing.", file=sys.stderr)
        sys.exit(1)

    logger.info("Yamlr Sovereign Proxy Active (Hardened)")
    # Explicitly use binary buffers for JSON-RPC stability
    stdin = getattr(sys.stdin, "buffer", sys.stdin)
    stdout = getattr(sys.stdout, "buffer", sys.stdout)
    proxy_server.start_io(stdin, stdout)

if __name__ == "__main__":
    start_lsp()
