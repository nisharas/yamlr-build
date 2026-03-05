"""
Yamlr LSP Server - Diagnostics Engine
-------------------------------------
Wraps the core Yamlr healing engine for real-time IDE feedback.
"""
import sys
import os
import logging
from typing import List, Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_DID_CHANGE,
    INITIALIZED,
    Diagnostic,
    Position,
    Range,
    DiagnosticSeverity,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DidChangeTextDocumentParams,
    InitializedParams,
)

# Add Yamlr source to path for the LSP process
# Hierarchy: d:\yamlr\vscode\lsp\server.py -> d:\yamlr\src
SOURCE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if SOURCE_ROOT not in sys.path:
    sys.path.append(SOURCE_ROOT)

from yamlr.core.engine import YamlrEngine

class YamlrLanguageServer(LanguageServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine: Optional[YamlrEngine] = None
        self.workspace_root: Optional[str] = None

    def initialize_engine(self, root_path: str):
        """Lazily initialize the engine with the workspace root."""
        if not self.engine or self.workspace_root != root_path:
            self.workspace_root = root_path
            # Use YamlrEngine.quick for fast startup
            self.engine = YamlrEngine(workspace_path=root_path)
            self.show_message(f"Yamlr Engine Initialized for: {root_path}")

server = YamlrLanguageServer("yamlr-lsp", "v1.1.0")

@server.feature(INITIALIZED)
async def initialized(ls: YamlrLanguageServer, params: InitializedParams):
    """Occurs when the client and server are fully connected."""
    if ls.workspace.root_path:
        ls.initialize_engine(ls.workspace.root_path)

@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: YamlrLanguageServer, params: DidOpenTextDocumentParams):
    """Occurs when a document is opened."""
    if not ls.engine and ls.workspace.root_path:
        ls.initialize_engine(ls.workspace.root_path)
    _validate(ls, params.text_document.uri)

@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: YamlrLanguageServer, params: DidSaveTextDocumentParams):
    """Occurs when a document is saved."""
    _validate(ls, params.text_document.uri)

@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: YamlrLanguageServer, params: DidChangeTextDocumentParams):
    """Occurs when a document is modified (as-you-type)."""
    # For on-type, we validate on every change. 
    # Real-time squiggles are a P0 for developers.
    _validate(ls, params.text_document.uri)

def _validate(ls: YamlrLanguageServer, uri: str):
    """
    Core validation logic: Passes document to YamlrEngine and returns LSP Diagnostics.
    """
    if not ls.engine:
        return

    doc = ls.workspace.get_text_document(uri)
    content = doc.source
    
    opts = getattr(ls, "initialization_options", {})
    if not isinstance(opts, dict):
        # pygls object mapping fallback
        opts = opts.__dict__ if hasattr(opts, '__dict__') else {}

    harden = bool(opts.get('harden', False))
    strict = bool(opts.get('strictValidation', False))
    enforce_limits = bool(opts.get('enforceLimits', False))
    enforce_probes = bool(opts.get('enforceProbes', False))

    # 1. Run Yamlr Engine on the raw content via stdin/stream mode
    # audit_stream returns a HealFileResult object
    result = ls.engine.audit_stream(
        content,
        harden=harden,
        strict_validation=strict,
        enforce_limits=enforce_limits,
        enforce_probes=enforce_probes
    )
    
    diagnostics = []
    
    # 2. Map Yamlr Findings to LSP Diagnostics
    findings = result.get("findings", [])
    for issue in findings:
        # Determine Severity
        sev_str = issue.get("severity", "ERROR").upper()
        severity = DiagnosticSeverity.Error
        if sev_str == "WARNING":
            severity = DiagnosticSeverity.Warning
        elif sev_str == "INFO":
            severity = DiagnosticSeverity.Information

        # Map Line/Char (Yamlr uses 1-indexed lines)
        line = max(0, issue.get("line_number", 1) - 1)
        
        # Heuristic for highlighting: Highlight the first 80 chars or the offending line
        # Future enhancement: Use actual start/end char from the engine if available
        d = Diagnostic(
            range=Range(
                start=Position(line=line, character=0),
                end=Position(line=line, character=80), 
            ),
            message=f"{issue.get('message')} (Yamlr: {issue.get('rule_id')})",
            severity=severity,
            source="yamlr",
            code=issue.get("rule_id"),
            data={"remediation": issue.get("remediation_hint")}
        )
        diagnostics.append(d)
    
    # 3. Publish results to the client
    ls.publish_diagnostics(uri, diagnostics)

if __name__ == "__main__":
    # Setup logging to stderr so it doesn't interfere with IO protocol
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    server.start_io()
