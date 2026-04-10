"""
Help Formatter for Yamlr CLI — Dispatcher.

Why: Keeps cli/main.py lean by externalizing help text. The monolithic
     print_subcommand_help() was decomposed into per-command modules
     in cli/help/ to enforce the 500-line modularity limit and prevent
     duplicate elif entries.

Architecture:
    - print_kubectl_help(): Main help menu (unchanged, lives here).
    - print_subcommand_help(): Thin dispatcher to per-command modules.
    - Per-command help lives in cli/help/help_scan.py, help_heal.py,
      help_toolbox.py, help_utils.py.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-28
"""

from typing import Any, Dict, List, Optional

from rich.panel import Panel
from rich.table import Table

from yamlr.cli.constants import COMMAND_TIER_MAP, CommandTier

__all__ = ["print_kubectl_help", "print_subcommand_help"]

DIM_WHITE = "dim white"

# All commands with task-oriented descriptions
# Why: Moved to module level to reduce cognitive complexity of help functions.
DESCRIPTIONS = {
    "scan": "Check manifests for issues (read-only, safe default)",
    "heal": "Preview and apply fixes (interactive by default)",
    "check": "Fast syntax & schema validation (great for CI)",
    "upgrade": "Migrate deprecated APIs to a target K8s version",
    "status": "Show backups, receipts, and recent heal activity",
    "doctor": "Check Yamlr installation, catalogs, and environment",
    "rules": "List protections and rule IDs",
    "explain": "Explain a specific rule or finding",
    "secure": "Analyze & suggest security hardening (Pro)",
    # Advanced (Advanced help only)
    "graph": "Visual Observability: Relational topology & blast-radius",
    "stats": "Engineering Efficiency: Surgical impact & team mastery",
    "roi": "Executive Portfolio: Financial impact & budget justification",
    "dna": "Calculate/Verify Semantic SHA-256 DNA for provenance",
    "pulse": "Founder Intelligence: Global rule efficacy & ROI telemetry",
    "evidence": "Generate Auditor-Ready compliance reports (PDF/JSON)",
    "mcp": "Model Context Protocol: Connect Yamlr to AI Agents (Pro)",
    "baseline": "Snapshot current violations to ignore them in future scans",
    "idp-export": "Platform Integration: Export safety truth [backstage|prometheus]",
    "init": "Initialize a new project with .yamlr.yaml",
    "restore": "Restore files from backups",
    "diagnose": "Run deep-dive analysis with debug support bundles",
    "auth": "Manage Yamlr Enterprise (Pro) authentication",
    "version": "Display version info and license status",
    "welcome": "Onboarding: Quick start & branding",
    "completion": "Generate shell autocompletion scripts",
    "catalog": "Manage Kubernetes schema definitions",
    "manual": "Open command manuals or full user guide",
    "demo": "Watch Yamlr heal a broken cluster (interactive simulation)",
    "lsp": "Start the Protocol (LSP) Server for VS Code (Pro)",
    "drift": "Reconcile live cluster state against local manifests (Pro)",
    "rollback": "Roll back the last atomic healing session (Omega)",
}

GROUPINGS = {
    "scan": ["audit"],
    "upgrade": ["migrate"],
}
ALIASES = ["audit", "migrate"]


def _add_help_tier(console, title, tier, color, show_all: bool):
    """Helper to add rows to tier tables.

    Why: Extracted to reduce cognitive complexity of print_kubectl_help.
    """
    # We only show Non-PRIMARY tiers if show_all is true

    if not show_all and tier == CommandTier.ADVANCED:
        return

    console.print(f"\n[bold gold1]┌─ {title}[/bold gold1]")
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column(style=f"bold {color}", width=18)
    table.add_column(style="italic grey70")

    found = False
    for cmd, cmd_tier in COMMAND_TIER_MAP.items():
        if cmd_tier == tier:
            if cmd in ALIASES:
                continue

            display_cmd = cmd
            if cmd in GROUPINGS:
                display_cmd = f"{cmd} / {' / '.join(GROUPINGS[cmd])}"

            desc = DESCRIPTIONS.get(cmd, "...")
            table.add_row(display_cmd, desc)
            found = True

    if found:
        console.print(table)


def print_kubectl_help(console, invoked_as: str, show_all: bool = False):
    """Displays the main help menu in a tiered, journey-inspired format.

    Why: Minimizing cognitive load for new users while preserving
         power-user features behind a progressive disclosure gate (--all).
    """

    # Header - Minimalist
    console.print(
        Panel(
            f"[bold cyan]{invoked_as.lower()}[/bold cyan] — Kubernetes manifest safety & healing engine",
            border_style="cyan",
            expand=False,
        )
    )

    # Journey Tiers
    _add_help_tier(console, "START HERE", CommandTier.PRIMARY, "green", show_all)
    _add_help_tier(console, "WHEN YOU'RE READY", CommandTier.SECONDARY, "cyan", show_all)

    # Advanced Tier (Only shown with --all)
    if show_all:
        _add_help_tier(console, "ADVANCED & PLATFORM", CommandTier.ADVANCED, "magenta", show_all)

    # Global Options
    console.print("\n[bold gold1]┌─ GLOBAL OPTIONS[/bold gold1]")
    opt_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    opt_table.add_column(style="yellow", width=24)

    # Logic: if plain, use no style, otherwise use DIM_WHITE
    desc_style = "" if getattr(console, "_yamlr_plain", False) else DIM_WHITE
    opt_table.add_column(style=desc_style)
    opt_table.add_row("-h, --help", "Show this help")
    opt_table.add_row("--all", "Show all commands (advanced)")
    opt_table.add_row("--kube-version VERSION", "Target K8s version (e.g., 1.28, v1.31)")
    opt_table.add_row("--output CHOICE", "Output format: text (default), json, sarif")
    opt_table.add_row("--timing", "Show surgical execution timing breakdown")
    opt_table.add_row("--timing-file FILE", "Save performance profile to JSON file")
    opt_table.add_row("-q, --quiet", "Minimal output (CI/CD)")
    opt_table.add_row("--verbose", "Detailed engine logs")
    console.print(opt_table)

    # Quick Examples (Centered/Prominent)
    console.print("\n[bold gold1]┌─ QUICK EXAMPLES[/bold gold1]")
    qs_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    qs_table.add_column(style="cyan", width=24)
    qs_table.add_column(style="" if getattr(console, "_yamlr_plain", False) else DIM_WHITE)
    qs_table.add_row("yamlr scan .", "Audit all YAML files (no changes)")
    qs_table.add_row("yamlr heal pod.yaml", "Preview a repair with visual diff")
    qs_table.add_row("yamlr check .", "Fast syntax & schema validation")
    qs_table.add_row("yamlr explain [id]", "Why this rule fired and how to fix it")
    console.print(qs_table)

    # Trust Guarantee (One-liner)
    console.print("\n[bold gold1]┌─ TRUST GUARANTEE[/bold gold1]")
    console.print("Yamlr analyzes manifests locally and never sends your YAML to external servers.")

    console.print("\n[bold gold1]┌─ NEXT STEPS[/bold gold1]")
    console.print("  [bold deep_sky_blue1]• Discover:[/bold deep_sky_blue1] Run [bold light_cyan1]yamlr features[/bold light_cyan1] to see the capability matrix")
    console.print("  [bold deep_sky_blue1]• Audit:[/bold deep_sky_blue1]    Run [bold light_cyan1]yamlr scan[/bold light_cyan1] [bold bright_magenta].[/bold bright_magenta] to check your current workspace")
    console.print("  [bold deep_sky_blue1]• Heal:[/bold deep_sky_blue1]     Run [bold light_cyan1]yamlr heal[/bold light_cyan1] [bold bright_magenta].[/bold bright_magenta] for interactive, safe remediation")

    # Discovery Tips
    tip_text = (
        f"• Run [bold deep_sky_blue1]{invoked_as} <command> --help[/bold deep_sky_blue1] for subcommand flags\n"
        f"• Run [bold deep_sky_blue1]{invoked_as} manual <command>[/bold deep_sky_blue1] for deep technical user guides\n"
        f"• Run [bold deep_sky_blue1]{invoked_as} --help --all[/bold deep_sky_blue1] to see all advanced commands\n"
        "• Docs: [link=https://yamlr.dev]https://yamlr.dev[/link]"
    )
    console.print(Panel(tip_text, title="[bold gold1]💡 TIP[/bold gold1]", border_style="gold1", expand=False))


def print_subcommand_help(console, command: str, invoked_as: str, show_all: bool = False):
    """Dispatches to per-command help modules.

    Why: Replaced the monolithic 260-line elif chain that had 6
         duplicate entries. Each command group now lives in its own
         module under cli/help/.
    """
    # Lazy imports to avoid circular dependencies
    from yamlr.cli.help.help_toolbox import (
        help_diagnose,
        help_drift,
        help_dna,
        help_evidence,
        help_secure,
        help_upgrade,
    )
    from yamlr.cli.help.help_scan import help_scan, help_check, help_audit
    from yamlr.cli.help.help_heal import help_heal
    from yamlr.cli.help.help_observability import (
        help_graph,
        help_idp_export,
        help_pulse,
    )
    from yamlr.cli.help.help_utils import (
        help_auth,
        help_catalog,
        help_completion,
        help_demo,
        help_explain,
        help_init,
        help_lsp,
        help_manual,
        help_mcp,
        help_restore,
        help_roi,
        help_rollback,
        help_rules,
        help_stats,
        help_status,
        help_version,
        help_welcome,
    )

    # Dispatch table — deterministic, no duplicate elif entries
    dispatch = {
        "scan": lambda: help_scan(console, invoked_as, show_all),
        "check": lambda: help_check(console, invoked_as, show_all),
        "audit": lambda: help_audit(console, invoked_as, show_all),
        "heal": lambda: help_heal(console, invoked_as, show_all),
        "diagnose": lambda: help_diagnose(console, invoked_as, show_all),
        "secure": lambda: help_secure(console, invoked_as, show_all),
        "upgrade": lambda: help_upgrade(console, "upgrade", invoked_as, show_all),
        "migrate": lambda: help_upgrade(console, "migrate", invoked_as, show_all),
        "dna": lambda: help_dna(console, invoked_as),
        "evidence": lambda: help_evidence(console, invoked_as),
        "catalog": lambda: help_catalog(console, invoked_as),
        "version": lambda: help_version(console, invoked_as),
        "explain": lambda: help_explain(console, invoked_as),
        "auth": lambda: help_auth(console, invoked_as),
        "init": lambda: help_init(console, invoked_as),
        "restore": lambda: help_restore(console, invoked_as),
        "demo": lambda: help_demo(console, invoked_as),
        "welcome": lambda: help_welcome(console, invoked_as),
        "completion": lambda: help_completion(console, invoked_as),
        "status": lambda: help_status(console, invoked_as),
        "rules": lambda: help_rules(console, invoked_as),
        "stats": lambda: help_stats(console, invoked_as),
        "roi": lambda: help_roi(console, invoked_as),
        "graph": lambda: help_graph(console, invoked_as),
        "idp-export": lambda: help_idp_export(console, invoked_as),
        "pulse": lambda: help_pulse(console, invoked_as),
        "manual": lambda: help_manual(console, invoked_as),
        "mcp": lambda: help_mcp(console, invoked_as),
        "lsp": lambda: help_lsp(console, invoked_as),
        "drift": lambda: help_drift(console, invoked_as, show_all),
        "rollback": lambda: help_rollback(console, invoked_as),
        "features": lambda: help_features(console, invoked_as),
        "baseline": lambda: help_baseline(console, invoked_as),
        "doctor": lambda: help_doctor(console, invoked_as),
    }

    handler = dispatch.get(command)
    if handler:
        handler()
