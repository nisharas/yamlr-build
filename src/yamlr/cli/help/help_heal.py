"""
Help text for the 'heal' command.

Why: Groups the complex healing-specific help logic. Separated from the
     module to keep help_formatter.py under 500 lines and enable
     independent updates for Safety Engine output framing.
"""

from __future__ import annotations

from rich.table import Table

from .shared import print_semantic_protection_options, print_shared_analysis_options

__all__ = ["help_heal"]


def help_heal(console, invoked_as: str, show_all: bool = False) -> None:
    """Display help for the 'heal' command with task-based recipes."""
    console.print("\n[bold green]┌─ USAGE[/bold green]")
    console.print(f"  [bold white]{invoked_as} heal <target...>[/bold white] [options]")

    # Safety Guarantee (One-liner)
    console.print(
        "\n[bold yellow]🛡 SAFETY:[/bold yellow] Automatic backups are created in [bold].yamlr/backups[/bold] before any write operation."
    )

    # Recipes (Always shown)
    console.print("\n[bold magenta]┌─ RECIPES[/bold magenta]")
    rec_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    rec_table.add_column(style="cyan", width=24)
    rec_table.add_column(style="white")
    rec_table.add_row(f"{invoked_as} heal .", "Preview: Show visual diff of proposed repairs")
    rec_table.add_row(f"{invoked_as} heal . -y", "Apply: Auto-confirm and write all repairs")
    rec_table.add_row(f"{invoked_as} heal . --harden", "Pro: Apply PSR-Restricted security hardening")
    console.print(rec_table)

    console.print("\n[bold cyan]┌─ OPTIONS[/bold cyan]")
    console.print("  target              File(s), directory(s), or '-' for stdin")
    console.print("  --dry-run, --diff   Show proposed fixes without writing")
    console.print("  -y, --yes-all       Auto-confirm all repairs (Safe Batch)")
    console.print("  --receipt           Generate DNA-signed compliance receipt")

    if show_all:
        console.print("\n[bold magenta]┌─ SURGICAL INJECTION[/bold magenta]")
        console.print("  --enforce-limits    Inject standard CPU/RAM requests & limits")
        console.print("  --enforce-probes    Inject default Liveness/Readiness probes")
        console.print("  --enforce-namespace Inject default namespace if missing")
        console.print("  --fix-tags          Auto-remediate :latest or missing image tags")
        
        console.print("\n[bold magenta]┌─ ENTERPRISE REMEDIATION (PRO)[/bold magenta]")
        console.print("  --fix-refs          Cross-Resource Auto-Fix: Repair selectors and port mismatches")
        console.print("  --complement-mode   Ingest findings from Checkov/Kubeconform (tool:path)")
        console.print("  --evidence-dir DIR  Compile receipts into auditor-ready reports")
        console.print("  --adapters-dir DIR  Ingest custom Python/Shell remediation adapters")
        
        console.print("\n[bold magenta]┌─ ADVANCED[/bold magenta]")
        console.print("  --unsafe [kind]     Allow healing of sensitive resources (e.g. Secret)")
        console.print("  --no-backup         Skip creation of .yamlr/backups/ (Dangerous)")
        print_shared_analysis_options(console, show_all)
        print_semantic_protection_options(console, is_heal=True, show_all=show_all)

    if not show_all:
        console.print(
            f"\n[dim]💡 Tip: Run '{invoked_as} heal --help --all' to see cross-resource selectors, SRE profiles, and audit-trail flags.[/dim]"
        )
