"""
WELCOME COMMAND - The Interactive Onboarding
--------------------------------------------
Displays the brand banner and quick-start guide.
"""
from yamlr.core.entrypoints.display import print_custom_header
from yamlr.core.entrypoints.base import get_console, CORE_VERSION
from yamlr.core.bridge import YamlrBridge
from rich.align import Align
from rich.columns import Columns
from rich.console import Group, Console
from rich.panel import Panel
from rich.table import Table

def handle_welcome_command(args, engine, is_pro: bool):
    """
    Displays the Yamlr welcome experience with a 'Premium' dashboard layout.
    
    Why: Habit formation. Converts Yamlr from a one-off tool into a 
         persistent project guardian by showing cumulative progress.
    """
    console = get_console()
    invoked_as = YamlrBridge.get_invoked_command()
    
    # 1. Print Bolder Header
    print_custom_header(invoked_as, is_pro, center=True)
    
    # 2. Layout construction
    # Core Actions Panel
    core_actions = Table(show_header=False, box=None, padding=(0, 1))
    core_actions.add_column(style="cyan bold")
    core_actions.add_column()
    core_actions.add_row("scan", "Audit manifests (SARIF support)")
    core_actions.add_row("check", "Fast CI/CD syntax gate")
    core_actions.add_row("heal", "Propose repairs (Dry-run by default)")
    core_actions.add_row("secure", "Analyze & suggest security hardening (Pro)")
    core_actions.add_row("init", "Initialize .yamlr.yaml config")
    core_actions.add_row("restore", "Revert changes from backups")
    core_actions.add_row("demo", "Launch 'Magic Moment' sample")
    
    core_panel = Panel(
        core_actions, 
        title="[bold white]⚡ Core Workflows[/bold white]", 
        border_style="cyan", 
        padding=(1, 2)
    )

    # Scaling & CI Panel
    scaling_info = Table(show_header=False, box=None, padding=(0, 1))
    scaling_info.add_column(style="magenta bold")
    scaling_info.add_column()
    scaling_info.add_row("Enterprise Scaling", "Verified for 70k+ files")
    scaling_info.add_row("CI throughput", "~50 files/sec (multi-proc)")
    scaling_info.add_row("Memory Safety", "O(1) growth with streaming")
    scaling_info.add_row("rules", "See active protections")
    scaling_info.add_row("status", "System & Catalog health")

    help_panel = Panel(
        scaling_info, 
        title="[bold white]🚀 Enterprise Readiness[/bold white]", 
        border_style="magenta", 
        padding=(1, 2)
    )

    # 3. Quick Audit CTA & Storytelling
    cta_text = (
        "[bold white]Ready for a Quick Win?[/bold white]\n"
        f"Run [cyan bold]yamlr scan .[/cyan bold] to see how your manifests rank against [green bold]v{engine.cluster_version}[/green bold] standards."
    )
    
    norway_tip = (
        "[bold yellow]Did you know?[/bold yellow]\n"
        "The 'Norway Problem' (country code [bold]NO[/bold] becoming [bold]false[/bold]) "
        "is a classic YAML trap. Yamlr identifies and heals these automatically."
    )

    cta_panel = Panel(
        Align.center(cta_text),
        title="[bold green]🎯 Recommended Next Step[/bold green]",
        border_style="green",
        padding=(1, 1)
    )
    
    tip_panel = Panel(
        Align.center(norway_tip),
        title="[bold yellow]💡 Pro Tip[/bold yellow]",
        border_style="yellow",
        padding=(1, 1)
    )

    # 4. Capability Spotlight Panel
    spotlight_text = (
        "✨ [bold green]Ghost Services:[/bold green] Detect dangling services with no matching Pods.\n"
        "✨ [bold green]Risk Intelligence:[/bold green] Heuristic-based impact analysis and blast-radius tracking.\n"
        "✨ [bold green]Zero-Trust Security:[/bold green] Auto-inject default-deny NetPols & PSS Restricted.\n"
        "✨ [bold green]Cross-Resource:[/bold green] Catch port mismatches, broken Ingress, and orphans.\n"
        "✨ [bold green]API Migration:[/bold green] Upgrades deprecated K8s APIs to modern stable versions.\n"
        "✨ [bold green]Resource Optimizer:[/bold green] Intelligently auto-injects CPU/Memory requests & limits."
    )
    spotlight_panel = Panel(
        spotlight_text,
        title="[bold green]🦾 Power Healing Spotlight[/bold green]",
        border_style="green",
        padding=(1, 2)
    )

    # Privacy, Safety & Docs Panel
    discovery_text = (
        "🔎 [bold white]Discovery Master Key:[/bold white] Run [cyan bold]yamlr explain config/discovery[/cyan bold].\n"
        "✨ [bold white]Pro Tip:[/bold white] Use [yellow bold]--output sarif[/yellow bold] for GitHub Code Scanning visibility."
    )
    privacy_text = (
        "🔓 [bold white]Privacy First:[/bold white] All manifest processing happens locally.\n"
        "✨ [bold white]Intent-Driven:[/bold white] yamlr won't modify any files unless --yes is passed.\n"
        "⚙️ [bold white]Setup Tip:[/bold white] Run [cyan bold]yamlr init[/cyan bold] at your repo root before your first scan to set up global rules.\n"
        "📚 [bold white]Complete Manual:[/bold white] Run [magenta bold]yamlr manual[/magenta bold] for the offline guide."
    )
    discovery_panel = Panel(
        Group(discovery_text, privacy_text),
        title="[bold cyan]📖 Privacy, Safety & Documentation[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    )

    # 5. Project Mastery Dashboard (Telemetry)
    stats = engine.telemetry.get_stats()
    mastery_table = Table(show_header=False, box=None, padding=(0, 2))
    mastery_table.add_column(style="bold cyan")
    mastery_table.add_column(style="bold green")
    
    mastery_table.add_row("Total Scans Run", f"{stats.get('total_scans', 0):,}")
    mastery_table.add_row("Issues Auto-Fixed", f"{stats.get('total_fixed_issues', 0):,}")
    mastery_table.add_row("Est. SRE Time Saved", f"{int(stats.get('total_time_saved_minutes', 0))} mins")
    
    efficiency = stats.get("surgical_efficiency", 0.0)
    rank = "Novice"
    if efficiency > 100: rank = "Grandmaster"
    elif efficiency > 50: rank = "Architect"
    elif efficiency > 10: rank = "Surgical Lead"
    
    mastery_table.add_row("Surgical Efficiency", f"{efficiency:.1f}x")
    mastery_table.add_row("Project Rank", f"[{'green' if rank != 'Novice' else 'yellow'}]{rank}[/]")

    mastery_panel = Panel(
        mastery_table,
        title="[bold magenta]🏆 Project Mastery Dashboard[/bold magenta]",
        border_style="magenta",
        padding=(1, 2)
    )

    # Display Dashboard
    console.print(Columns([core_panel, mastery_panel], equal=True, expand=True))
    console.print(Columns([help_panel, discovery_panel], equal=True, expand=True))
    console.print(spotlight_panel)
    console.print(cta_panel)
    
    tier_label = "Enterprise" if is_pro else "Free Version"
    footer = (
        f"  [dim]Version: {CORE_VERSION} | Build: Stable | Identity: {tier_label}[/dim]\n"
        f"  [dim]Documentation: [link=https://yamlr.dev]https://yamlr.dev[/link] | Use [bold]yamlr completion --install[/bold] for autocomplete.[/dim]"
    )
    console.print(footer)
    
    return 0
