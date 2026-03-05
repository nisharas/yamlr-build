"""
DIAGNOSE COMMAND LOGIC
----------------------
A deep-dive debugging wrapper around the 'scan' command.
"""
import logging
from yamlr.core.entrypoints.scan import handle_scan_command

def handle_diagnose_command(args, engine, formatter):
    """
    Executes 'scan' with elevated verbosity for debugging.
    
    Equivalent to:
    yamlr scan --verbose --debug
    """
    # 1. Force Debug Mode
    # This enables full stack traces and internal decision logs
    logging.getLogger("yamlr").setLevel(logging.DEBUG)
    
    # 2. Mutate Arguments
    # Ensure options compatible with deep debugging are set
    args.verbose = True
    
    # 3. Delegate to Scan
    return handle_scan_command(args, engine, formatter)
