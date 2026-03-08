"""
STATS COMMAND - The Surgical ROI Calculator
--------------------------------------------
Displays cumulative project impact, time saved, and project mastery.
"""
import json
from pathlib import Path
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group
from rich import box

def handle_stats_command(args, engine, console):
    """
    Displays the project-wide surgical ROI and mastery metrics.
    """
    stats = engine.telemetry.get_stats()
    
    if getattr(args, 'output', 'text') == 'json':
        console.print_json(data=stats)
        return 0

    # Header
    console.print()
    console.print(Panel(
        Text("Yamlr Surgical ROI Dashboard", style="bold magenta"), 
        box=box.ASCII if getattr(console, "_yamlr_plain", False) else box.DOUBLE
    ))
    console.print()

    # Impact Grid
    impact_table = Table(title="[bold white]Cumulative Surgical ROI[/bold white]", show_header=True, box=box.SIMPLE_HEAD)
    impact_table.add_column("Key Metric", style="cyan")
    impact_table.add_column("Value", justify="right", style="green bold")
    impact_table.add_column("Value Metric Proof", style="dim")

    impact_table.add_row(
        "Files Audited", 
        f"{stats.get('total_scans', 0):,}", 
        "Unique project manifest audits"
    )
    impact_table.add_row(
        "Surgical Fixes", 
        f"{stats.get('total_fixed_issues', 0):,}", 
        "Automated corrections applied"
    )
    
    hours = stats.get('total_time_saved_minutes', 0) / 60.0
    impact_table.add_row(
        "Engineering Time Saved", 
        f"{hours:.1f} hrs", 
        "Reclaimed developer productivty"
    )
    
    # [VAL-02-7] Throughput Performance tracking
    throughput = stats.get("peak_throughput_fps", 0.0)
    if throughput > 0:
        impact_table.add_row(
            "Peak Throughput",
            f"{throughput:.1f} f/s",
            "Maximum file processing velocity"
        )

    efficiency = stats.get("surgical_efficiency", 0.0)
    impact_table.add_row(
        "Surgical Efficiency", 
        f"{efficiency:.1f}x", 
        "Avg issues resolved per session"
    )

    console.print(impact_table)

    # Mastery Progression
    rank = "Novice"
    progress_color = "yellow"
    if efficiency > 100: 
        rank = "Grandmaster (Legendary)"
        progress_color = "bright_magenta"
    elif efficiency > 50: 
        rank = "Architect (Elite)"
        progress_color = "bright_blue"
    elif efficiency > 10: 
        rank = "Surgical Lead"
        progress_color = "green"

    console.print(f"\n[bold white]Current Engineering Mastery:[/bold white] [{progress_color}]{rank}[/]")
    
    # Time Saved Highlight
    if hours >= 1.0:
        console.print(f"\n[bold green]✨ ROI PROOF: {hours:.1f} human engineering hours reclaimed via autonomous healing.[/bold green]")
    
    console.print("\n[dim]Telemetry is stored locally in .yamlr/telemetry.json to ensure zero-blindspot privacy.[/dim]\n")
    
    return 0
