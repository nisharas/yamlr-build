"""
STATS COMMAND - The Surgical ROI Calculator
--------------------------------------------
Displays cumulative project impact, time saved, and project mastery.
"""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from yamlr.core.telemetry import GlobalTelemetryManager

__all__ = ["handle_stats_command"]


def handle_stats_command(args, engine, console):
    """
    Displays the project-wide and global surgical ROI and mastery metrics.
    """
    local_stats = engine.telemetry.get_stats()
    global_mgr = GlobalTelemetryManager()
    global_stats = global_mgr.data

    if getattr(args, "output", "text") == "json":
        console.print_json(data={"local": local_stats, "global": global_stats})
        return 0

    if getattr(args, "apps", False):
        from yamlr.core.advisory import AdvisoryRenderer
        from yamlr.core.scoring import ScoringEngine

        # 1. Run a fresh scan to get findings
        if not getattr(console, "_yamlr_quiet", False):
            console.print("[dim]Analyzing application safety across workspace...[/dim]")

        target = args.path if hasattr(args, "path") and args.path else ["."]
        results = engine.batch_heal(target, dry_run=True)

        # 2. Group by Application
        app_results: Dict[str, List[Any]] = {}
        for res in results:
            # Heuristic: Use 'app' label or parent directory as app name
            app_name = "Infrastructure"
            if hasattr(res, "identities") and res.identities:
                for ident in res.identities:
                    # Look for app labels
                    labels = getattr(ident, "labels", {}) or {}
                    app_name = labels.get("app.kubernetes.io/name") or labels.get("app") or labels.get("yamlr.dev/app")
                    if app_name:
                        break

            if not app_name:
                # Fallback to parent directory name
                path = Path(res.file_path)
                app_name = path.parent.name if path.parent.name not in (".", "") else "Root"

            if app_name not in app_results:
                app_results[app_name] = []
            app_results[app_name].append(res)

        # 3. Generate app safety report
        scoring = ScoringEngine()  # Use default penalties
        report = scoring.generate_app_report(app_results)

        # 3. Render via advisory engine
        advisory = AdvisoryRenderer(console)
        advisory.render_app_stats(report)
        return 0

    if getattr(args, "badge", False):
        fixes = local_stats.get("total_fixed_issues", 0)
        hours = local_stats.get("total_time_saved_minutes", 0) / 60.0

        # Color logic
        color = "green" if fixes > 10 else "blue"
        if fixes > 50:
            color = "brightmagenta"

        badge_msg = f"{fixes}_Fixes" if fixes > 0 else "Safety_First"
        if hours >= 1.0:
            badge_msg += f"--{hours:.1f}_Hrs_Saved"

        badge_url = f"https://img.shields.io/badge/Yamlr_ROI-{badge_msg}-{color}"
        markdown = f"[![Yamlr ROI]({badge_url})](https://yamlr.dev)"

        console.print(markdown)
        return 0

    if getattr(args, "org", False):
        return _render_org_stats(console, global_mgr)

    # ... remaining code ...
    # Header
    console.print()
    console.print(
        Panel(
            Text("Yamlr Surgical ROI Dashboard", style="bold magenta"),
            box=box.ASCII if getattr(console, "_yamlr_plain", False) else box.DOUBLE,
        )
    )
    console.print()

    # Impact Grid (Dual Columns: Local vs Global)
    impact_table = Table(
        title="[bold white]Cumulative Surgical ROI (Budget Justification)[/bold white]",
        show_header=True,
        box=box.ASCII if getattr(console, "_yamlr_plain", False) else box.DOUBLE_EDGE,
        border_style="cyan",
    )
    impact_table.add_column("Metric", style="white")
    impact_table.add_column("This Project", justify="right", style="green bold")
    impact_table.add_column("Global Impact (All Projects)", justify="right", style="magenta bold")

    impact_table.add_row(
        "Files Audited", f"{local_stats.get('total_scans', 0):,}", f"{global_stats.get('total_scans', 0):,}"
    )
    impact_table.add_row(
        "Surgical Fixes",
        f"{local_stats.get('total_fixed_issues', 0):,}",
        f"{global_stats.get('total_fixed_issues', 0):,}",
    )

    local_hours = local_stats.get("total_time_saved_minutes", 0) / 60.0
    global_hours = global_stats.get("total_time_saved_minutes", 0) / 60.0
    impact_table.add_row("Engineering Time Saved", f"{local_hours:.1f} hrs", f"{global_hours:.1f} hrs")

    efficiency = local_stats.get("surgical_efficiency", 0.0)
    impact_table.add_row(
        "Surgical Efficiency",
        f"{efficiency:.1f}x",
        f"{global_stats.get('total_fixed_issues', 0) / max(1, global_stats.get('total_heals', 1)):.1f}x",
    )

    console.print(Align.center(impact_table))

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

    # Global Fleet Footprint
    if global_stats.get("total_projects", 0) > 1:
        console.print(
            f"[dim]Aggregated across {global_stats.get('total_projects')} active workspaces on this machine.[/dim]"
        )

    # Enterprise Feature Usage (Pro/Enterprise)
    pro_usage = global_stats.get("pro_usage", {})
    if pro_usage:
        console.print("\n[bold gold3]Enterprise Feature Activations (Pro):[/]")
        pro_table = Table(show_header=False, box=box.SIMPLE, border_style="gold3")
        for feature, count in pro_usage.items():
            pro_table.add_row(f" • {feature.replace('_', ' ').title()}", f"{count:,} times")
        console.print(pro_table)

    # ROI Proof Highlight
    if global_hours >= 1.0:
        msg = f"\n[bold green]💰 GLOBAL ROI PROOF: {global_hours:.1f} human engineering hours reclaimed via autonomous healing.[/bold green]"
        console.print(Panel(msg, border_style="green", expand=False))

    console.print("\n[dim]Telemetry is stored locally in .yamlr/ to ensure 100% privacy and data integrity.[/dim]\n")

    return 0


def _render_org_stats(console, global_mgr):
    """Renders the executive organization-wide ROI dashboard."""
    summary = global_mgr.get_org_summary()
    impact = summary["org_impact"]
    efficiency = summary["efficiency_metrics"]
    pro_usage = summary["pro_usage"]

    console.print()
    console.print(
        Panel(
            Text("Yamlr Organizational ROI Report (Executive Suite)", style="bold gold1"),
            subtitle="Cumulative impact across all engineering teams",
            border_style="gold1",
            box=box.ASCII if getattr(console, "_yamlr_plain", False) else box.DOUBLE,
        )
    )
    console.print()

    # Impact Grid
    grid = Table(show_header=True, box=box.SIMPLE, border_style="dim")
    grid.add_column("Category", style="cyan")
    grid.add_column("Value", style="bold green")
    grid.add_column("Efficiency Score", style="dim")

    grid.add_row(
        "Active Workspaces", f"{impact['total_projects']:,}", "High" if impact["total_projects"] > 5 else "Growing"
    )
    grid.add_row("Total Scans/Heals", f"{impact['total_surgical_events']:,} / {impact['total_heals']:,}", "Autonomous")
    grid.add_row(
        "Auto-Fixed Issues",
        f"{impact['total_fixed_issues']:,}",
        f"{efficiency['avg_fixes_per_project']:.1f} per project",
    )
    grid.add_row("Total Time Saved", f"{impact['total_hours_saved']:,} hours", "Immediate ROI")

    console.print(grid)

    if pro_usage:
        console.print("\n[bold cyan]Enterprise Feature Adoption:[/]")
        for feature, count in pro_usage.items():
            console.print(f"  • {feature.replace('_', ' ').title()}: [bold magenta]{count:,}[/bold magenta] uses")

    console.print(
        Panel(
            f"[bold green]Strategic Verdict:[/bold green] Yamlr has reclaimed [bold white]{impact['total_hours_saved']}[/bold white] hours of engineering time. "
            "This represents a significant reduction in technical debt and operational risk.",
            border_style="green",
            padding=(1, 2),
        )
    )
    return 0
