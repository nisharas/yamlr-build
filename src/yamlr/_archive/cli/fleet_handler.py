"""CLI handler for Yamlr fleet commands.

Why: Keeps CLI handling modular and under the 500-line limit by
isolating multi-repo GitOps batching logic from core command handlers.
"""
import logging
import sys
from pathlib import Path
from typing import Any

from yamlr.core.fleet_batcher import FleetBatcher
from yamlr.ui.theme import COLOR_ACCENT, COLOR_SUCCESS, console

logger = logging.getLogger(__name__)


def cmd_fleet_dispatch(args: Any) -> int:
    """Dispatches fleet commands to inventory overview or PR batching."""
    sub = getattr(args, "fleet_command", None)

    if sub == "pr-batch":
        return _handle_pr_batch(args)

    # Default fallback: multi-cluster context inventory
    from yamlr.core_logic import cmd_fleet
    cmd_fleet()
    return 0


def _handle_pr_batch(args: Any) -> int:
    """Executes multi-repo manifest remediation and PR batching."""
    target = getattr(args, "repos", ".")
    branch = getattr(args, "branch", "yamlr/fleet-upgrade")
    title = getattr(args, "title", "fix(k8s): automated fleet manifest remediation")
    apply = getattr(args, "apply", False)
    dry_run = getattr(args, "dry_run", False)
    create_pr = getattr(args, "create_pr", False)
    report_path = getattr(args, "report", "fleet-report.md")

    console.print(f"[{COLOR_ACCENT}][*] Yamlr Fleet Batcher: Initializing discovery for '{target}'...[/{COLOR_ACCENT}]")
    batcher = FleetBatcher()
    repos = batcher.discover_repositories(target)

    if not repos:
        console.print(f"[bold red][!] No git repositories discovered in '{target}'.[/bold red]")
        return 1

    console.print(f"[{COLOR_SUCCESS}][+] Discovered {len(repos)} repository(ies). Processing...[/{COLOR_SUCCESS}]")
    summary = batcher.batch_process(
        repositories=repos,
        branch=branch,
        title=title,
        apply=apply,
        create_pr=create_pr,
        dry_run=dry_run
    )

    from rich.table import Table
    table = Table(title="Yamlr Fleet Batch Summary", border_style="dim")
    table.add_column("Repository", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Modified Files", justify="right")
    table.add_column("Rules Triggered", justify="right")
    table.add_column("Details", style="dim")

    for r in summary["results"]:
        status_color = "green" if r["status"] in ["CLEAN", "PR_CREATED", "HEALED"] else "yellow"
        table.add_row(
            r["repo"],
            f"[{status_color}]{r['status']}[/{status_color}]",
            str(r["modified_files_count"]),
            str(r["rules_triggered"]),
            r.get("pr_url") or r.get("error") or "Ready"
        )

    console.print(table)

    if report_path:
        batcher.generate_report(summary, report_path)
        console.print(f"[{COLOR_SUCCESS}][+] Generated fleet report at: {report_path}[/{COLOR_SUCCESS}]")

    return 0
