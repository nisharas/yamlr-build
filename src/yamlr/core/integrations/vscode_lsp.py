"""
Yamlr VS Code Language Server (LSP)
----------------------------------
Provides real-time Kubernetes manifest diagnostics and Quick-Fix actions
for the Yamlr VS Code extension.

Architecture:
- Protocol: LSP (Language Server Protocol)
- Transport: JSON-RPC over stdio
- SDK: pygls (Python Language Server)

Supported Capabilities:
- textDocument/publishDiagnostics: Real-time scan findings
- textDocument/codeAction: One-click "Heal" actions for specific rules

Author: Nishar A Sunkesala / Yamlr Team
Why: To provide the 'Developer Desktop' habit trigger mentioned in the Roadmap.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

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
        TextEdit,
        WorkspaceEdit,
    )
    from pygls.lsp.server import LanguageServer

    HAS_PYGLS = True
except ImportError:
    HAS_PYGLS = False
    # Fallback constants for type checking/decorators
    TEXT_DOCUMENT_DID_OPEN = "textDocument/didOpen"
    TEXT_DOCUMENT_DID_CHANGE = "textDocument/didChange"
    TEXT_DOCUMENT_CODE_ACTION = "textDocument/codeAction"

    class DidOpenTextDocumentParams:
        pass

    class DidChangeTextDocumentParams:
        pass

    class CodeActionParams:
        range: Any
        text_document: Any

    class PublishDiagnosticsParams:
        def __init__(self, uri: str, diagnostics: List[Diagnostic]):
            self.uri = uri
            self.diagnostics = diagnostics

    class Diagnostic:
        pass

    class DiagnosticSeverity:
        Error = 1
        Warning = 2
        Information = 3

    class Position:
        pass

    class Range:
        pass

    class CodeAction:
        pass

    class CodeActionKind:
        QuickFix = "quickfix"

    class Command:
        pass


# Fallback for type checking
if not HAS_PYGLS:

    class LanguageServer:
        def __init__(self, *args, **kwargs):
            """Initializes the fallback LSP server class."""
            pass

        def thread(self, *args, **kwargs):
            """Fallback thread decorator."""
            return lambda f: f

        def feature(self, *args, **kwargs):
            """Fallback feature decorator."""
            return lambda f: f

        def command(self, *args, **kwargs):
            """Fallback command decorator."""
            return lambda f: f

        def start_io(self):
            """Fallback IO start method."""
            pass

        def publish_diagnostics(self, *args, **kwargs):
            """Fallback diagnostic publisher."""
            pass


# 🛡 Total Stream Isolation: Save real stdout for LSP, then muzzle sys.stdout globally.
# This prevents native prints (like 'b-b') from polluting the JSON-RPC pipe.
_real_stdout = sys.stdout
sys.stdout = sys.stderr

# Setup logging to stderr exclusively
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("yamlr.lsp")


class YamlrLanguageServer(LanguageServer):
    def __init__(self):
        super().__init__("yamlr-lsp", "v1.0")
        self.engine: Optional[Any] = None
        self._diagnostics_cache: Dict[str, List[Diagnostic]] = {}

    def get_engine(self):
        """Lazy-load the Yamlr Engine."""
        if not self.engine:
            from yamlr.core.engine.base import YamlrEngine

            # Initialize engine in the current workspace with safe-mode defaults
            self.engine = YamlrEngine(workspace_path=".", safe_mode=True)
        return self.engine


server = YamlrLanguageServer()


@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: YamlrLanguageServer, params: DidOpenTextDocumentParams):
    """Scan file when opened."""
    analyze_and_publish(ls, params.text_document.uri)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: YamlrLanguageServer, params: DidChangeTextDocumentParams):
    """Scan file when changed (with debounce)."""
    analyze_and_publish(ls, params.text_document.uri)


def analyze_and_publish(ls: YamlrLanguageServer, uri: str):
    """Bridge Yamlr Engine findings to LSP Diagnostics using in-memory streams."""
    if not HAS_PYGLS:
        return

    try:
        from urllib.parse import unquote

        # 🛡️ URI Integrity: Decode URL-encoded characters (e.g. %3A -> :)
        path = unquote(uri.replace("file://", ""))

        # Normalize Windows paths
        if os.name == "nt":
            if path.startswith("/"):
                path = path[1:]
            path = path.replace("/", "\\")

        logger.info(f"Analyzing {uri} (decoded: {path})")

        # Get current document content from the LS buffer (real-time)
        # 🛡️ API Compatibility: Support pygls <1.0 (get_document) and >=1.0 (get_text_document)
        if hasattr(ls.workspace, "get_text_document"):
            doc = ls.workspace.get_text_document(uri)
        elif hasattr(ls.workspace, "get_document"):
            doc = ls.workspace.get_document(uri)
        else:
            # Final fallback for extremely new/old versions
            doc = getattr(ls.workspace, "documents", {}).get(uri)

        if not doc:
            logger.warning(f"Could not find document for {uri} in workspace")
            return

        content = doc.source

        engine = ls.get_engine()
        # [Forensic Audit] Execute the engine in 'audit_stream' mode for real-time diagnostics
        result = engine.audit_stream(content, source_name=path)

        diagnostics = []
        findings = getattr(result, "findings", [])
        logger.info(f"Engine returned {len(findings)} findings for {path}")

        for finding in findings:
            # Map Yamlr finding to LSP Diagnostic
            msg = finding.get("message", "Yamlr Finding")
            rule_id = finding.get("rule_id", "yamlr")
            rationale = finding.get("rationale", "")
            severity_str = (finding.get("severity") or "WARNING").upper()

            # Use DiagnosticSeverity (0-indexed)
            l_severity = DiagnosticSeverity.Warning
            if severity_str == "ERROR":
                l_severity = DiagnosticSeverity.Error
            elif severity_str == "INFO":
                l_severity = DiagnosticSeverity.Information

            # LSP Diagnostic Range (0-indexed)
            # Ensure line and column are never None; default to 1 (which becomes 0)
            line = (finding.get("line") or 1) - 1
            col = (finding.get("column") or 1) - 1

            full_msg = f"yamlr: {rule_id}\n\nObservation: {msg}"
            if rationale:
                full_msg += f"\n\nRationale: {rationale}"

            # Simple 1-line range for now.
            diag_range = Range(
                start=Position(line=max(0, line), character=max(0, col)), end=Position(line=max(0, line), character=80)
            )

            diag = Diagnostic(
                range=diag_range,
                message=full_msg,
                severity=l_severity,
                source="yamlr",
                code=rule_id,
                data={"suggestion": finding.get("suggestion")},
            )
            diagnostics.append(diag)

        ls._diagnostics_cache[uri] = diagnostics

        # 🛡️ pygls 2.x Protocol: Wrap in PublishDiagnosticsParams object
        params = PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
        ls.text_document_publish_diagnostics(params)
        logger.info(f"Successfully published {len(diagnostics)} diagnostics for {uri}")

    except Exception:
        import traceback

        logger.error(f"LSP Protocol Failure for {uri}:\n{traceback.format_exc()}")


@server.feature(TEXT_DOCUMENT_CODE_ACTION)
def code_action(ls: YamlrLanguageServer, params: CodeActionParams) -> List[CodeAction]:
    """Provide Quick-Fix actions based on scan findings."""
    if not HAS_PYGLS:
        return []

    actions = []
    uri = params.text_document.uri

    # Check current diagnostics at the cursor position
    diagnostics = ls._diagnostics_cache.get(uri, [])
    for diag in diagnostics:
        # Check if cursor intersects diagnostic range
        if diag.range.start.line <= params.range.start.line <= diag.range.end.line:
            suggestion = diag.data.get("suggestion")
            if suggestion:
                # Create a "Heal this file" command
                # In a more advanced version, we'd use WorkspaceEdit for instant apply.
                # For now, we launch a command that the client will handle.

                action = CodeAction(
                    title=f"Yamlr: {suggestion}",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diag],
                    command=Command(title="Yamlr: Heal File", command="yamlr.healFile", arguments=[uri, diag.code]),
                )
                actions.append(action)

    return actions


@server.command("yamlr.healFile")
def heal_file_command(ls: YamlrLanguageServer, args: List[Any]):
    """Server-side command to apply a specific heal."""
    # This would ideally return a WorkspaceEdit back to the client.
    # For now, we'll log it and let the Node.js client trigger the engine if needed.
    logger.info(f"Heal command received: {args}")


def start_lsp(_args=None):
    """Main entry point for 'yamlr lsp'."""
    if not HAS_PYGLS:
        print("Error: 'pygls' is required for LSP mode. Install with: pip install pygls", file=sys.stderr)
        return 1

    logger.info("Yamlr Forensic Safety Engine Active")
    # ✅ MANDATORY: Use raw binary streams (.buffer) for JSON-RPC transport
    # to prevent TypeError: cannot use a bytes pattern on a string-like object
    stdin = getattr(sys.stdin, "buffer", sys.stdin)
    stdout = getattr(_real_stdout, "buffer", _real_stdout)
    server.start_io(stdin, stdout)
    return 0


if __name__ == "__main__":
    start_lsp()
