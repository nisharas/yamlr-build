"""
CHECK COMMAND LOGIC
-------------------
A fast, syntax-only wrapper around the 'scan' command.
d"""
from __future__ import annotations
from yamlr.core.entrypoints.scan import handle_scan_command
__all__ = ['handle_check_command']


def handle_check_command(args, engine):
    """
    Executes 'scan' in fast mode (Syntax + Schema only).
    
    Equivalent to:
    yamlr scan --fast
    """
    # 1. Mutate Arguments for Speed
    # We want to skip network calls (OPA, Catalog Fetch) if possible 
    
    return handle_scan_command(args, engine)
