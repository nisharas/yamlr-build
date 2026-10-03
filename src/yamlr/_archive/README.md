# Yamlr Legacy Python Engine Archive

## Context & Architecture
As part of the **Ruff Model** architectural transition:
- The entire Kubernetes manifest parsing, healing, topology analysis, policy enforcement, LSP server, and CLI dispatch have migrated 100% to native Rust (`native_core/`).
- The Python distribution package (`yamlr`) is now a streamlined Ruff-style distribution package containing:
  - `__init__.py`: Fast in-memory Python API (`heal_yaml`, `scan_yaml`, etc.) delegating directly to `yamlr_native`.
  - `__main__.py`: Zero-overhead sub-millisecond passthrough to the compiled native binary (`yamlr.exe` / `yamlr`).
  - `_find_bin.py`: Multi-tier binary discovery.
  - `version.py`: Version declaration.

## Archive Contents
This directory (`src/yamlr/_archive/`) preserves all previous Python engine components:
- `cli/`: Legacy Python CLI argument parser, dispatch, and formatters
- `core/`: Legacy pipeline, backups, and stages
- `knowledge/`: CIS benchmark and knowledge rules
- `ui/`: Rich-based terminal renderers and diff viewers
- `sarif_reporter.py`, `lsp.py`, `mcp_server.py`, `webhook/`: Historical standalone Python daemons

## Retention Policy
Per project guardrails, **no code is deleted**. These files are preserved for historical reference, forensic audit verification, and non-destructive compatibility.
