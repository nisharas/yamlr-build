"""
SECURE COMMAND LOGIC
--------------------
A security-focused wrapper around the 'heal' command.
"""
from __future__ import annotations
from yamlr.core.entrypoints.heal import handle_heal_command
__all__ = ['handle_secure_command']


def handle_secure_command(args, engine, is_pro: bool):
    """
    Executes 'heal' with security hardening forced ON.
    
    Equivalent to:
    yamlr heal --harden
    """
    # 1. Force Security Flags
    args.harden = True
    
    # 2. Delegate to Heal
    return handle_heal_command(args, engine, is_pro)
