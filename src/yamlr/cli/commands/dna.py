#!/usr/bin/env python3
"""
DNA CLI COMMAND - Wrapper for Semantic DNA operations.
"""

from yamlr.core.entrypoints.dna import handle_dna_command

def handle_dna_cli_command(args, engine, console):
    """
    Exposes the DNA command to the CLI.
    """
    return handle_dna_command(args, engine, console)
