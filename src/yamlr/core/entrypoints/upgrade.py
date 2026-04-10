"""
UPGRADE COMMAND LOGIC (High-Fidelity)
------------------------------------
Provides a visually stunning conversion experience for Free users.
"""

from __future__ import annotations

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from yamlr.core.bridge import YamlrBridge

__all__ = ["handle_upgrade_command"]


def handle_upgrade_command(args, engine, console: Console) -> int:
    """Displays the high-fidelity upgrade comparison dashboard.

    Why: To drive Pro conversion through a premium, "Google-Level"
         visual experience that highlights the value of auto-healing.
    """
    is_pro = YamlrBridge.is_pro_enabled()

    if is_pro:
        console.print(
            Panel(
                "[bold green]✨ You are already on Yamlr Pro![/bold green]\n\n"
                "You have access to all high-gravity healing engines and enterprise compliance packs.",
                title="Pro Status",
                border_style="green",
            )
        )
        return 0

    _render_upgrade_dashboard(console)

    checkout_url = YamlrBridge.get_auth_url()
    console.print("\n[bold gold1]PRO UPGRADE HINT[/bold gold1]")
    console.print("[bold white]Ready to unlock the full power of Yamlr?[/bold white]")
    console.print(f"[bold cyan]👉 Upgrade now at:[/bold cyan] [link={checkout_url}]{checkout_url}[/link]")
    console.print("[dim]Run `yamlr auth --login` after purchase to activate your session.[/dim]\n")

    return 0


def _render_upgrade_dashboard(console: Console):
    """Renders the feature comparison matrix using Rich."""

    table = Table(
        title="[bold white]Yamlr Free vs. Yamlr Pro[/bold white]",
        show_header=True,
        header_style="bold magenta",
        box=None,
        padding=(0, 2),
    )

    table.add_column("Capability", style="dim", width=40)
    table.add_column("Free", justify="center")
    table.add_column("Pro", justify="center")

    # 1. Parsing & Observation (Free)
    table.add_row("Tolerant K8s Parsing", "✅", "✅")
    table.add_row("Comment & Formatting Sync", "✅", "✅")
    table.add_row("Issue Detection (100+ rules)", "✅", "✅")

    table.add_section()

    # 2. Basic Healing (Free)
    table.add_row("Lexical & Syntax Repair", "✅", "✅")
    table.add_row("Schema Typo Correction", "✅", "✅")
    table.add_row("Version Migrations (v1.9-v1.35)", "✅", "✅")

    table.add_section()

    # 3. High-Gravity Surgery (Pro)
    table.add_row(
        "[bold cyan]Relational Surgery (--fix-refs)[/bold cyan]",
        "[red]Scan Only[/red]",
        "✅ [bold green]Auto-Fix[/bold green]",
    )
    table.add_row(
        "[bold cyan]Security Hardening (--harden)[/bold cyan]",
        "[red]Scan Only[/red]",
        "✅ [bold green]Auto-Fix[/bold green]",
    )
    table.add_row(
        "[bold cyan]Resource Optimization[/bold cyan]", "[red]Scan Only[/red]", "✅ [bold green]Auto-Fix[/bold green]"
    )

    table.add_section()

    # 4. Enterprise Compliance (Pro)
    table.add_row("[bold gold1]SOC2/HIPAA/CIS Rule Packs[/bold gold1]", "❌", "✅")
    table.add_row("[bold gold1]Signed DNA Performance Receipts[/bold gold1]", "❌", "✅")
    table.add_row("[bold gold1]Interactive HTML/PDF Reports[/bold gold1]", "❌", "✅")

    # "Glassmorphism" effect via Panel
    console.print(
        Panel(
            table,
            border_style="bright_blue",
            title="[bold white]SURGICAL TIER COMPARISON[/bold white]",
            subtitle="[dim]The 'Supplier' Class K8s Healing Engine[/dim]",
        )
    )

    # ROI Highlight
    console.print(
        Columns(
            [
                Panel(
                    "[bold green]+70%[/bold green]\n[dim]Avg. Healing Rate Upgrade[/dim]",
                    border_style="green",
                    expand=True,
                ),
                Panel(
                    "[bold cyan]~4.2 hrs[/bold cyan]\n[dim]SRE Time Saved / Week[/dim]",
                    border_style="cyan",
                    expand=True,
                ),
                Panel(
                    "[bold magenta]100%[/bold magenta]\n[dim]Compliance Integrity[/dim]",
                    border_style="magenta",
                    expand=True,
                ),
            ]
        )
    )
