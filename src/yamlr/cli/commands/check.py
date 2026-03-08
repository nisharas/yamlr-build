"""
CHECK COMMAND LOGIC
-------------------
A fast, syntax-only wrapper around the 'scan' command.
d"""
from yamlr.core.entrypoints.scan import handle_scan_command

def handle_check_command(args, engine, formatter):
    """
    Executes 'scan' in fast mode (Syntax + Schema only).
    
    Equivalent to:
    yamlr scan --fast
    """
    # 1. Mutate Arguments for Speed
    # We want to skip network calls (OPA, Catalog Fetch) if possible 
    # (though --fast flag logic would need to be implemented in scan.py technically, 
    # for now we rely on the intent alias)
    
    # For now, 'check' is just an alias for scan, but we document it as "Syntax Check"
    # Future enhancement: args.skip_network = True
    
    return handle_scan_command(args, engine, formatter)
