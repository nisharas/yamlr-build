"""
ROI COMMAND - The Founder's Executive Dashboard
-----------------------------------------------
Displays high-fidelity ROI metrics, cost savings, and budget justification.
"""

from __future__ import annotations

import json

from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from yamlr.core.telemetry import GlobalTelemetryManager

__all__ = ["handle_roi_command"]


def handle_roi_command(args, engine, console):
    """
    Displays the executive ROI and budget justification metrics.
    """
    local_stats = engine.telemetry.get_stats()
    global_mgr = GlobalTelemetryManager()
    global_stats = global_mgr.data

    if getattr(args, "output", "text") == "json":
        import sys

        data = {
            "local": local_stats,
            "global": global_stats,
            "valuation_metrics": {
                "hourly_rate": 100.0,
                "local_wealth_reclaimed": (local_stats.get("total_time_saved_minutes", 0) / 60.0) * 100.0,
                "global_wealth_reclaimed": (global_stats.get("total_time_saved_minutes", 0) / 60.0) * 100.0,
            },
        }
        sys.stdout.write(json.dumps(data, indent=2) + "\n")
        return 0

    if getattr(args, "badge", False):
        hours = local_stats.get("total_time_saved_minutes", 0) / 60.0
        wealth = hours * 100.0

        # Color logic
        color = "green" if wealth > 1000 else "blue"
        if wealth > 5000:
            color = "brightmagenta"

        badge_msg = f"Reclaimed_${wealth:,.0f}"
        if hours >= 1.0:
            badge_msg += f"--{hours:.1f}_Hrs"

        badge_url = f"https://img.shields.io/badge/Yamlr_Wealth-{badge_msg}-{color}"
        markdown = f"[![Yamlr Wealth Reclaimed]({badge_url})](https://yamlr.dev)"

        console.print(markdown)
        return 0

    # Executive Header
    console.print()
    console.print(
        Panel(
            Text("Executive Portfolio Insights", style="bold green", justify="center"),
            subtitle="[dim]Budgets & Organizational Efficiency Proof[/dim]",
            box=box.ASCII if getattr(console, "_yamlr_plain", False) else box.DOUBLE_EDGE,
            border_style="green",
        )
    )
    console.print()

    # Wealth Table
    wealth_table = Table(
        show_header=True,
        box=box.SIMPLE_HEAD if getattr(console, "_yamlr_plain", False) else box.ROUNDED,
        border_style="green",
    )
    wealth_table.add_column("Key Valuation Metric", style="white")
    wealth_table.add_column("Impact Value", justify="right", style="green bold")

    local_hours = local_stats.get("total_time_saved_minutes", 0) / 60.0
    global_hours = global_stats.get("total_time_saved_minutes", 0) / 60.0

    # Assumptions
    HOURLY_RATE = 100.0  # Standard Engineering Rate
    local_value = local_hours * HOURLY_RATE
    global_value = global_hours * HOURLY_RATE

    wealth_table.add_row("Engineering Time Reclaimed", f"{local_hours:.1f} Hours")
    wealth_table.add_row("Total Wealth Reclaimed (Est.)", f"[bold]${local_value:,.2f}[/]")
    wealth_table.add_row(
        "Risk Prevention Surface", f"{local_stats.get('total_fixed_issues', 0):,} Potential Outages Defused"
    )

    console.print(Align.center(wealth_table))

    # Global Organization Impact
    if global_stats.get("total_projects", 0) > 1:
        console.print("\n[bold white]Organization-Wide Proof of Value:[/bold white]")
        console.print(f" • [cyan]Workspaces Powered:[/cyan] {global_stats.get('total_projects')}")
        console.print(f" • [cyan]Global Reclaimed Wealth:[/cyan] [bold]${global_value:,.2f}[/]")
        console.print(
            f" • [cyan]Mission-Critical Fixes:[/cyan] {global_stats.get('total_fixed_issues', 0):,} across fleet"
        )

    # The "$20M Narrative" Box
    console.print()
    narrative = (
        "This report translates technical improvements into organizational value. "
        "[bold green]Wealth Reclaimed[/bold green] represents engineering budget recovered via "
        "autonomous manifest healing. [bold cyan]Shadow Risk[/bold cyan] is the aggregate risk prevented "
        "from entering production. Aggregated data provides proof of organizational efficiency "
        "and manifest asset integrity."
    )
    console.print(Panel(narrative, title="[bold]Strategic Context[/bold]", border_style="cyan", padding=(1, 2)))

    console.print(
        "\n[dim]ROI derived from weighted SRE intervention benchmarks (Basic Fix: 2m, Logic Fix: 15m, Security: 30m, Migration: 60m).[/dim]"
    )
    console.print(
        "[dim]Aggregated local data is used to prove organizational efficiency and manifest asset integrity.[/dim]\n"
    )

    return 0
