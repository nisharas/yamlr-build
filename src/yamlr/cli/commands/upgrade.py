"""
UPGRADE COMMAND LOGIC
---------------------
A version-aware wrapper around the 'heal' command.
"""
from yamlr.core.entrypoints.heal import handle_heal_command

def handle_upgrade_command(args, engine, formatter, is_pro: bool):
    """
    Executes 'heal' with a focus on API migration.
    
    Equivalent to:
    yamlr heal --check-deprecations --diff (default)
    """
    # 1. Force Deprecation Checks
    args.check_deprecations = True
    
    # 2. Safety Defaults
    # If neither --yes nor --dry-run is set, default to dry-run (preview)
    # The 'heal' command usually prompts, but for upgrade we want explicit diff first behavior
    if not getattr(args, "yes", False) and not getattr(args, "dry_run", False):
         args.dry_run = True # Force preview mode by default
    
    # 3. Delegate to Heal
    # The Engine is already initialized with the correct target version
    # because main.py resolved it from --to argument.
    return handle_heal_command(args, engine, formatter, is_pro)
