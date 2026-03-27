"""
PULSE COMMAND HANDLER
----------------------
Displays aggregated founder intelligence and ecosystem ROI.
"""
from __future__ import annotations
from yamlr.core.telemetry import PulseManager
from yamlr.core.entrypoints.base import get_console
from rich.table import Table
from rich.panel import Panel

__all__ = ['handle_pulse_command']

def handle_pulse_command(args, _engine, console=None):
    """
    Displays the 'Pulse' of the Yamlr ecosystem on this machine.
    
    Why: To provide the founder with a clear view of product impact 
         and ROI across all managed workspaces.
    """
    if console is None:
        console = get_console()
        
    pm = PulseManager()
    intel = pm.get_founder_intelligence()
    
    if args.output == "json":
        console.print_json(data=intel)
        return 0

    console.print(Panel(
        "[bold cyan]📊 Yamlr Founder Intelligence (Pulse)[/bold cyan]\n"
        "Strategic metrics aggregated across all local workspaces.",
        border_style="cyan"
    ))

    # 1. Ecosystem Health Table
    health = intel["ecosystem_health"]
    health_table = Table(title="Ecosystem Health", box=None)
    health_table.add_column("Metric", style="dim")
    health_table.add_column("Value", style="bold green")
    
    health_table.add_row("Active Workspaces", str(health["total_workspaces"]))
    health_table.add_row("Total Surgical Events", str(health["total_surgical_events"]))
    health_table.add_row("Total Issues Fixed", str(health["total_fixes"]))
    health_table.add_row("Cumulative Hours Saved", f"{health['cumulative_hours_saved']}h")
    
    console.print(health_table)

    # 2. Pro Adoption
    pro = intel["pro_adoption"]
    if pro:
        console.print("\n[bold]💎 Pro Feature Adoption[/bold]")
        pro_table = Table(box=None)
        pro_table.add_column("Feature", style="dim")
        pro_table.add_column("Usage", style="blue")
        for feature, count in pro.items():
            pro_table.add_row(feature.replace("_", " ").title(), str(count))
        console.print(pro_table)

    # 3. Anonymized Projects
    projects = intel["anonymized_projects"]
    if projects:
        console.print("\n[bold]📂 Active Projects (Anonymized)[/bold]")
        for p in projects:
            console.print(f"  • {p}")

    console.print(f"\n[dim]Engine Version: {intel['engine_version']}[/dim]")
    console.print("[dim italic]Note: All data is stored locally in ~/.yamlr/global_stats.json[/dim]\n")
    
    return 0
