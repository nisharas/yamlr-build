"""
Help text for utility commands: catalog, version, auth, init, restore,
demo, welcome, completion, status, rules, stats, manual.

Why: Groups the simple, low-flag subcommand help texts that don't
     need complex shared helpers. Keeps per-module line counts low.
"""

from __future__ import annotations

from typing import Any, List

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .shared import OPTIONS_HEADER, OUTPUT_JSON_FLAG

__all__ = [
    "help_catalog",
    "help_version",
    "help_explain",
    "help_auth",
    "help_init",
    "help_restore",
    "help_demo",
    "help_welcome",
    "help_completion",
    "help_status",
    "help_rules",
    "help_stats",
    "help_roi",
    "help_manual",
    "help_mcp",
    "help_lsp",
    "help_rollback",
    "render_upgrade_advisory",
]


def help_catalog(console, invoked_as: str) -> None:
    """Display help for the 'catalog' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} catalog <action>[/bold white] [options]")
    console.print("\n[bold cyan]ACTIONS[/bold cyan]")
    console.print("  update   Download latest schemas from upstream")
    console.print("  list     Show installed local catalogs")
    console.print("  status   Show current catalog resolution info")
    console.print(OPTIONS_HEADER)
    console.print("  --kube-version V    Target version for catalog operations")


def help_version(console, invoked_as: str) -> None:
    """Display help for the 'version' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} version[/bold white]")
    console.print("\nDisplays detailed version information for the client, engine, and active catalog.")


def help_explain(console, invoked_as: str) -> None:
    """Display help for the 'explain' command."""
    console.print(f"[bold green]USAGE[/bold green]  [bold white]{invoked_as} explain <rule_id>[/bold white]")
    console.print("Shows detailed documentation for a single rule.")
    console.print("Run without a rule_id to list all available rules.")
    console.print("[yellow]Tip:[/yellow] Use 'yamlr rules' to discover rule IDs.")


def help_auth(console, invoked_as: str) -> None:
    """Display help for the 'auth' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} auth <action>[/bold white]")
    console.print("\n[bold cyan]ACTIONS[/bold cyan]")
    console.print("  login    Connect to Yamlr Enterprise (Pro) and activate license")
    console.print("  logout   Clear local authentication tokens")
    console.print("  status   Display current license and user info")
    console.print("  whoami   Alias for 'auth status'")
    console.print("\n[dim]Yamlr Enterprise (Pro) features require a valid enterprise license.[/dim]")


def help_init(console, invoked_as: str) -> None:
    """Display help for the 'init' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} init[/bold white] [options]")
    console.print("\nCreates a default [bold].yamlr.yaml[/bold] configuration file in the current directory.")
    console.print("Use this to customize rule thresholds and file ignores.")
    console.print(OPTIONS_HEADER)
    console.print("  --force             Overwrite existing .yamlr.yaml file")
    console.print("  --output FORMAT     Report format (text, json)")


def help_restore(console, invoked_as: str) -> None:
    """Display help for the 'restore' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} restore <path...>[/bold white]")
    console.print("\nRecovers a file from the latest SRE backup in [bold].yamlr/backups[/bold].")
    console.print("Use this to undo accidental healing or manual edits.")


def help_demo(console, invoked_as: str) -> None:
    """Display help for the 'demo' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} demo[/bold white]")
    console.print(
        "\nCreates a [bold]yamlr-demo/[/bold] directory with malformed "
        "K8s manifests.\nThis is the fastest way to showcase Yamlr's "
        "healing capabilities."
    )


def help_welcome(console, invoked_as: str) -> None:
    """Display help for the 'welcome' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} welcome[/bold white]")
    console.print("\nDisplays the interactive Yamlr onboarding dashboard, offering a guided visual tour")
    console.print("and immediate entry points into the engine's core capabilities.")


def help_completion(console, invoked_as: str) -> None:
    """Display help for the 'completion' command."""
    console.print(
        f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} completion <shell> [--install][/bold white]"
    )
    console.print("\n[bold cyan]SHELLS[/bold cyan]")
    console.print("  bash         Generate completion script for Bash")
    console.print("  zsh          Generate completion script for Zsh")
    console.print("  fish         Generate completion script for Fish")
    console.print("  powershell   Generate completion script for PowerShell")
    console.print(OPTIONS_HEADER)
    console.print("  --install    Automatically install to your shell profile")
    console.print("  --word       (Internal) The current word being completed")
    console.print("  --position   (Internal) The cursor position in the line")
    console.print(
        "\n[bold yellow]TIP:[/bold yellow] Use [bold]yamlr completion "
        "--install[/bold] for zero-config autocomplete setup."
    )


def help_status(console, invoked_as: str) -> None:
    """Display help for the 'status' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} status[/bold white] [options]")
    console.print(
        "\nDisplays the SRE Dashboard, including configuration health, catalog status, and backup storage usage."
    )
    console.print(OPTIONS_HEADER)
    console.print("  --output json       Export dashboard data as structured JSON")
    console.print("  --kube-version V    Check status against specific K8s version")


def help_rules(console, invoked_as: str) -> None:
    """Display help for the 'rules' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} rules[/bold white] [options]")
    console.print("\nDisplays a comprehensive dashboard of all active semantic protections and compliance rules.")
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print(OUTPUT_JSON_FLAG)
    console.print("  -v, --verbose       Show full rationale for every rule")


def help_stats(console, invoked_as: str) -> None:
    """Display help for the 'stats' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} stats[/bold white] [options]")
    console.print(
        "\nDisplays project-wide Engineering Efficiency metrics, focusing on surgical impact and technical mastery."
    )
    console.print(OPTIONS_HEADER)
    console.print("  --output {text,json} Target output format")
    console.print("\n[dim]Efficiency ranks: Novice -> Surgical Lead -> Architect -> Grandmaster[/dim]")


def help_roi(console, invoked_as: str) -> None:
    """Display help for the 'roi' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} roi[/bold white] [options]")
    console.print(
        "\nDisplays the Executive ROI Portfolio, translating technical "
        "fixes into reclaimed engineering budget and financial value."
    )
    console.print(OPTIONS_HEADER)
    console.print("  --output {text,json} Target output format")


def help_manual(console, invoked_as: str) -> None:
    """Display help for the 'manual' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} manual[/bold white]")
    console.print("This is the definitive reference for all engine capabilities and configuration options.")


def help_mcp(console, invoked_as: str) -> None:
    """Display help for the 'mcp' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} mcp[/bold white] [options]")
    console.print("\nStarts the [bold cyan]Model Context Protocol (MCP) Server[/bold cyan].")
    console.print(
        "This allows AI Agents (like Antigravity or Claude) to use Yamlr as a tool for manifest analysis and healing."
    )
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  --transport {stdio}  Communication transport (default: stdio)")
    console.print("\n[dim]✨ Yamlr Enterprise (Pro) license is required for AI Agent integration.[/dim]")


def help_lsp(console, invoked_as: str) -> None:
    """Display help for the 'lsp' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} lsp[/bold white]")
    console.print("\nStarts the [bold cyan]Language Server Protocol (LSP) Server[/bold cyan].")
    console.print(
        "This is used by the [bold white]Yamlr VS Code Extension[/bold white] to provide real-time\n"
        "forensics, schema validation, and safe healing directly in your IDE."
    )
    console.print("\n[dim]✨ Yamlr Enterprise (Pro) license is required for LSP features.[/dim]")


def help_rollback(console, invoked_as: str) -> None:
    """Display help for the 'rollback' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} rollback[/bold white] [session_id]")
    console.print("\n[bold red]Omega Rollback[/bold red]: Reverses the last atomic healing transaction.")
    console.print(
        "Use this if a mass-fix was interrupted or caused unexpected side-effects.\n"
        "Yamlr keeps 100% comment-preserving snapshots of every modified file."
    )
    console.print("\n[bold cyan]ARGUMENTS[/bold cyan]")
    console.print("  session_id          ID of the transaction to revert (default: latest)")


def render_upgrade_advisory(console, current_v: str, target_v: str, risk_score: int, findings: List[Any]) -> None:
    """Displays a high-trust 'Safety Advisory' for K8s version upgrades.

    Why: Replaces alarming 'Hazard' UI with a supportive framework that
         emphasizes Yamlr's ability to provide a healing path.
    """

    # Determine Safety Level
    if risk_score >= 80:
        level = "CRITICAL"
        style = "bold red"
        icon = "🚨"
    elif risk_score >= 40:
        level = "MODERATE"
        style = "bold yellow"
        icon = "⚠️"
    else:
        level = "STABLE"
        style = "bold green"
        icon = "✅"

    # Header Panel
    header = Panel(
        Text.assemble(
            (f"{icon} UPGRADE SAFETY ADVISORY: {level}\n", style),
            (f"Targeting Kubernetes v{target_v} (from v{current_v})", "dim"),
        ),
        border_style=style,
        padding=(1, 2),
    )
    console.print(header)

    # Risk Breakdown
    table = Table(box=None, padding=(0, 2))
    table.add_column("Category", style="cyan")
    table.add_column("Findings", justify="right")

    removals = sum(1 for f in findings if "removed" in f.get("message", "").lower())
    deprecations = sum(1 for f in findings if "deprecated" in f.get("message", "").lower())

    if removals:
        table.add_row("Breaking Removals", f"[bold red]{removals}[/bold red]")
    if deprecations:
        table.add_row("API Deprecations", f"[yellow]{deprecations}[/yellow]")

    if table.row_count > 0:
        console.print(table)
        console.print("")

    # The "Healing Path" (Trust Pillar)
    path_panel = Panel(
        "[bold cyan]Yamlr Healing Path Active[/bold cyan]\n\n"
        "• [white]Semantic DNA preserved[/white] during API migration\n"
        "• [white]Automated remediation available[/white] for all detected removals\n"
        "• [white]Validation gates[/white] ensure v1.31 compliance\n\n"
        "[dim]Run 'yamlr upgrade --apply' to execute these safety fixes automatically.[/dim]",
        title="[bold white]🛡️ Trust Pillar: Automatic Recovery[/bold white]",
        border_style="cyan",
        expand=False,
    )
    console.print(path_panel)
    console.print("")
