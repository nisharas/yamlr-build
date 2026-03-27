"""
Help text for toolbox commands: diagnose, secure, upgrade, migrate, dna, evidence.

Why: Groups the medium-complexity subcommand help texts that share
     a common pattern (USAGE + OPTIONS + standard flags). Keeps the
     main help_formatter.py lean.
"""
from __future__ import annotations
from .shared import print_shared_analysis_options, print_semantic_protection_options

__all__ = ['help_diagnose', 'help_secure', 'help_upgrade', 'help_dna', 'help_evidence']



def help_diagnose(console, invoked_as: str) -> None:
    """Display help for the 'diagnose' command.

    Why: Diagnose is the debug-mode entry point. Users need to know
         it enables DEBUG-level logging for engine tracing.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} diagnose <target...>[/bold white] [options]"
    )
    console.print(
        "\nRuns a deep audit with [bold yellow]DEBUG[/bold yellow] "
        "logging enabled.\nUse this to trace engine decisions or report bugs."
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to analyze")
    console.print("  --output FORMAT     Report format (text, json)")
    print_shared_analysis_options(console)
    print_semantic_protection_options(console, is_heal=False)


def help_secure(console, invoked_as: str) -> None:
    """Display help for the 'secure' command.

    Why: Secure is a Pro feature. Help text must clearly state
         what it enforces and that it requires a Pro license.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} secure <target...>[/bold white] [options]"
    )
    console.print(
        "\nApplies enterprise security hardening (Pro feature)."
    )
    console.print(
        "Powered by the [bold cyan]Shield Engine[/bold cyan], it detects and fixes:\n"
        "  • [yellow]SHD-001[/yellow]: Dangerous HostPath Exposures\n"
        "  • [yellow]SHD-002[/yellow]: Privilege Escalation Risks\n"
        "  • [yellow]SHD-003[/yellow]: Sensitive Volume Exposure\n"
        "  • [yellow]SHD-004[/yellow]: Host Namespace Leaks\n"
        "  • [yellow]SHD-005[/yellow]: Resource Starvation in High-Impact Workloads"
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to harden")
    console.print("  --dry-run           Show proposed changes without writing")
    console.print("  --diff              Show visual diff")
    console.print("  -y, --yes           Auto-confirm changes")
    console.print("  --output FORMAT     Report format (text, json)")
    print_shared_analysis_options(console)
    print_semantic_protection_options(console, is_heal=True)


def help_upgrade(console, command: str, invoked_as: str) -> None:
    """Display help for the 'upgrade' or 'migrate' commands.

    Why: Upgrade is the version-migration tool. The --to flag is
         REQUIRED and must be prominent in the help output.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} {command} <target...>[/bold white] [options]"
    )
    console.print(
        "\nMigrates deprecated Kubernetes APIs to their modern replacements."
    )
    console.print("Example: [dim]extensions/v1beta1 Deployment -> apps/v1[/dim]")
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  target              File(s) or directory(s) to upgrade")
    console.print("  --to VERSION        Target K8s version (e.g. 1.30). Defaults to cluster/latest.")
    console.print("  --dry-run           Show proposed changes without writing")
    console.print("  --diff              Show visual diff")
    console.print("  -y, --yes           Auto-confirm changes")
    console.print("  --output FORMAT     Report format (text, json)")
    print_shared_analysis_options(console)
    print_semantic_protection_options(console, is_heal=True)


def help_dna(console, invoked_as: str) -> None:
    """Display help for the 'dna' command.

    Why: DNA is the semantic integrity feature. Users must
         understand hash-based verification for CI pipelines.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} dna <path>[/bold white] [options]"
    )
    console.print(
        "\nCalculates or verifies the Semantic SHA-256 DNA of a manifest."
    )
    console.print(
        "The DNA is invariant to formatting, comments, and field ordering."
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  path                Path to the YAML manifest file")
    console.print("  --hash HASH         Expected hash for verification (returns exit 1 if mismatch)")
    console.print("  --output json       Export DNA as structured JSON")


def help_evidence(console, invoked_as: str) -> None:
    """Display help for the 'evidence' command.

    Why: Evidence is the compliance reporting tool. Users must know
         it aggregates DNA receipts into auditor-ready PDFs.
    """
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]"
        f"{invoked_as} evidence <dir>[/bold white] [options]"
    )
    console.print(
        "\nAggregates cryptographic DNA receipts into a unified "
        "PDF Compliance Report."
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  dir                 Directory containing JSON receipts (e.g., from --evidence-dir)")
    console.print("  --format FORMAT     Output format: pdf (default) or json")
    console.print("  --output FILE       Path to save the generated report")


