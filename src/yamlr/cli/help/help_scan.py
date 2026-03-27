"""
Help text for the 'scan', 'check', and 'audit' commands.

Why: Extracted from monolithic help_formatter.py to enforce the
     500-line modularity limit and enable independent updates
     when Safety Engine output framing is added.
"""
from __future__ import annotations
from .shared import print_shared_analysis_options, print_semantic_protection_options

__all__ = ['help_scan', 'help_check', 'help_audit']


def help_scan(console, invoked_as: str, show_all: bool = False) -> None:
    """Display help for the 'scan' command with task-based recipes."""
    console.print("\n[bold green]┌─ USAGE[/bold green]")
    console.print(f"  [bold white]{invoked_as} scan <target...>[/bold white] [options]")

    # Recipes (Always shown)
    console.print("\n[bold magenta]┌─ RECIPES[/bold magenta]")
    rec_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    rec_table.add_column(style="cyan", width=24)
    rec_table.add_column(style="white")
    rec_table.add_row(f"{invoked_as} scan .", "Local: Audit current directory (Safe Default)")
    rec_table.add_row(f"{invoked_as} scan . -q --output sarif", "CI: Minimal output with structured results")
    rec_table.add_row(f"{invoked_as} scan . --stream-to out.json", "Ultra-Scale: Stream results for 10k+ files")
    console.print(rec_table)

    console.print("\n[bold cyan]┌─ OPTIONS[/bold cyan]")
    console.print("  target              File(s), directory(s), or '-' for stdin")
    
    if show_all:
        console.print("  --opa-bundle URL    Path or URL to OPA bundle (Gatekeeper compatibility)")
        console.print("  --kyverno-report P  Path to Kyverno PolicyReport for Auto-Fix ingestion")
        console.print("  --evidence-dir DIR  Generate cryptographic DNA evidence receipts")
        console.print("  --adapters-dir DIR  Execute custom Python/Bash remediation scripts")

    print_shared_analysis_options(console, show_all)
    print_semantic_protection_options(console, is_heal=False, show_all=show_all)

    if not show_all:
        console.print(f"\n[dim]💡 Tip: Run '{invoked_as} scan --help --all' to see OPA, Kyverno, and custom adapter flags.[/dim]")


def help_check(console, invoked_as: str, show_all: bool = False) -> None:
    """Display help for the 'check' command."""
    console.print("\n[bold green]┌─ USAGE[/bold green]")
    console.print(f"  [bold white]{invoked_as} check <target...>[/bold white] [options]")
    
    console.print("\nFast syntax and schema validation. Logic-checks only (no network).")
    console.print("[dim]Optimized for CI/CD: Defaults to --strict --summary-only.[/dim]")

    console.print("\n[bold cyan]┌─ OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to check")
    console.print("  --output FORMAT     Report format (text, json, sarif)")
    
    if show_all:
        console.print("  --fast              Always enabled for check")
        print_shared_analysis_options(console, show_all)


def help_audit(console, invoked_as: str, show_all: bool = False) -> None:
    """Display help for the 'audit' command (alias for scan)."""
    console.print("\n[bold green]┌─ USAGE[/bold green]")
    console.print(f"  [bold white]{invoked_as} audit <target...>[/bold white] [options]")
    
    console.print("\nDeep compliance audit. Calculates [bold]Healing Accuracy Score (HAS)[/bold].")

    console.print("\n[bold cyan]┌─ OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to audit")
    
    if show_all:
        console.print("  --bench             Run in 'Scientific Mode' against a labeled corpus")
        console.print("  --stats             Show aggregate health score and MASTERY rank")
        console.print("  --verify RECEIPT    Verify a .yamlr-receipt.json against manifest")

    print_shared_analysis_options(console, show_all)
    print_semantic_protection_options(console, is_heal=False, show_all=show_all)
