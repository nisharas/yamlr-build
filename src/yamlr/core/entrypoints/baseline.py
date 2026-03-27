"""
Yamlr BASELINE ENTRYPOINT
-------------------------
Implements the 'baseline' command for GitOps Guard regression testing.
Snapshots existing violations to allow teams to focus on new regressions.
"""

from __future__ import annotations

__all__ = ["handle_baseline_command"]

import json
import logging
from pathlib import Path

from yamlr.core.entrypoints.base import get_console, extract_cli_options

logger = logging.getLogger("yamlr.baseline")

def handle_baseline_command(args, engine, is_pro: bool) -> int:
    """
    Executes the baseline snapshot logic.
    
    Why: To establish a "Safety Floor" for legacy repositories, enabling
         Yamlr to block ONLY new regressions in CI/CD.
    """
    console = get_console()
    options = extract_cli_options(args, is_pro, console)
    
    baseline_path = Path(args.output) if getattr(args, "output", None) else Path(engine.workspace) / ".yamlr-baseline.json"
    
    console.print("\n[bold cyan]🚀 Establishing Baseline Snapshot...[/bold cyan]")
    console.print(f"[dim]Workspace: {engine.workspace}[/dim]")
    
    # 1. Discover all manifests (or use provided paths)
    targets = options.targets if options.targets else ["."]
    manifest_paths = []
    
    for target in targets:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = (engine.workspace / target).resolve()
            
        if target_path.is_file():
            try:
                manifest_paths.append(str(target_path.relative_to(engine.workspace)))
            except ValueError:
                manifest_paths.append(str(target_path))
        elif target_path.is_dir():
            for _, rel_p in engine.manager.fs.crawl(target_path, options.extensions, options.max_depth):
                manifest_paths.append(rel_p)
    
    if not manifest_paths:
        console.print("[yellow]No manifests found. Nothing to baseline.[/yellow]")
        return 0
        
    console.print(f"🔍 Auditing {len(manifest_paths)} files for baseline...")
    
    # 2. Run Batch Scan (Dry-Run)
    results = []
    for target in targets:
        target_results = engine.batch_heal(
            root_path=target,
            extensions=options.extensions,
            max_depth=options.max_depth,
            dry_run=True,
            enforce_limits=options.enforce_limits,
            enforce_probes=options.enforce_probes,
            enforce_namespace=options.enforce_namespace,
            fix_tags=options.fix_tags,
            harden=options.harden,
            check_deprecations=options.check_deprecations,
            task_label="Baselining"
        )
        results.extend(target_results)
    
    # 3. Collect Fingerprints
    fingerprints = []
    total_findings = 0
    
    for res in results:
        for finding in res.findings:
            # Generate stable fingerprint
            fp = engine.config.generate_finding_fingerprint(finding)
            fingerprints.append(fp)
            total_findings += 1
            
    # 4. Save to File
    # Ensure uniqueness
    unique_fingerprints = sorted(list(set(fingerprints)))
    
    baseline_data = {
        "metadata": {
            "version": "1.1",
            "generator": "yamlr baseline",
            "finding_count": total_findings,
            "unique_fingerprints": len(unique_fingerprints),
            "workspace": str(engine.workspace.resolve())
        },
        "fingerprints": unique_fingerprints
    }
    
    try:
        baseline_path.write_text(json.dumps(baseline_data, indent=2), encoding="utf-8")
        console.print("\n[bold green]✅ Baseline Created![/bold green]")
        console.print(f"📦 Saved to: [cyan]{baseline_path}[/cyan]")
        console.print(f"📉 Captured [bold]{len(unique_fingerprints)}[/bold] unique violations.")
        console.print("\n[dim]Future scans using [bold]--baseline[/bold] will ignore these issues.[/dim]")
        return 0
    except Exception as e:
        console.print(f"[bold red]❌ Failed to save baseline:[/bold red] {e}")
        return 1
