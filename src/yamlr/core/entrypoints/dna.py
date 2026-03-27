#!/usr/bin/env python3
"""
DNA COMMAND - Semantic Manifest Verification
--------------------------------------------
Calculates or verifies the SHA-256 Semantic DNA of a manifest.
Used for mathematical trust and drift detection.
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path
from yamlr.core.context import HealContext
from yamlr.core.license_manager import LicenseManager

logger = logging.getLogger("yamlr.core.entrypoints.dna")
__all__ = ['handle_dna_command']


def handle_dna_command(args, engine, console):
    """
    Orchestrates Semantic DNA generation and verification.
    """
    path_val = args.path
    if isinstance(path_val, (list, tuple)):
        if not path_val:
            console.print("[red]Error: No path provided.[/red]")
            return 1
        path_val = path_val[0]

    file_path = Path(path_val).resolve()
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        return 1

    try:
        status, _ = LicenseManager.check_pro_status()
        capabilities = LicenseManager.resolve_capabilities()
        
        if not status.is_usable() or not capabilities.can_verify_dna:
            LicenseManager.notify_pro_required("Semantic DNA Pipeline")
            return 1
            
        from yamlr.core.dna_utils import calculate_semantic_dna

        # Load and Reconstruction logic (Simplified for DNA)
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        # Run minimal pipeline logic to get docs
        # We use the engine's internal logic to ensure consistency
        # Stage 1-3 (Scan) - Correct sequence
        shards = engine.pipeline.lexer.shard(raw_content)
        lexer_metadata = engine.pipeline.lexer.prepare_for_scanner(shards)
        engine.pipeline.scanner.set_lexer_context(lexer_metadata)
        identities = engine.pipeline.scanner.scan_shards(shards)
        
        # Stage 6 (Reconstruction) - We need docs for semantic DNA
        context = HealContext(
            raw_text=raw_content,
            shards=shards,
            identities=identities,
            cluster_version=engine.cluster_version
        )
        docs = engine.pipeline.structurer.reconstruct(context)
        
        current_dna = calculate_semantic_dna(docs)

        # Mode: Verify
        if getattr(args, "expected_hash", None):
            if current_dna == args.expected_hash:
                console.print(f"[green]✅ DNA Verified: {current_dna}[/green]")
                return 0
            else:
                console.print("[red]❌ DNA Mismatch![/red]")
                console.print(f"  Expected: {args.expected_hash}")
                console.print(f"  Actual:   {current_dna}")
                return 1

        # Mode: Generate
        if getattr(args, "output", "text") == "json":
            import json
            sys.stdout.write(json.dumps({"path": str(file_path), "dna": current_dna}, indent=2) + "\n")
        else:
            console.print("\n[bold cyan]🧬 Semantic DNA (SHA-256):[/bold cyan]")
            console.print(f"[bold white]{current_dna}[/bold white]")
            console.print("[dim]Generated from stabilized semantic structure (ignores formatting/comments).[/dim]\n")
        
        return 0

    except Exception as e:
        console.print(f"[red]Error during DNA calculation: {e}[/red]")
        logger.error(f"DNA calculation failed: {e}")
        return 1
