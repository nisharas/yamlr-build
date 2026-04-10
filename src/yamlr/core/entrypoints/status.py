"""
STATUS COMMAND - The SRE Dashboard
----------------------------------
Shows system health, backup usage, and catalog status.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from rich import box
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

BOLD_WHITE = "bold white"
BOLD_YELLOW = "bold yellow"
DIM_NA = "[dim]N/A[/dim]"

from yamlr.core.catalog_manager import CatalogManager

__all__ = ["handle_status_command"]


def get_bench_metrics(workspace: Path) -> dict:
    """Calculates scientific HAS metrics from local benchmark data."""
    bench_file = workspace / "yamlr_bench_latest.json"
    metrics = {"lexical_has": 0.0, "schema_has": 0.0, "semantic_has": 0.0, "total_files": 0}

    if not bench_file.exists():
        return metrics

    try:
        lex_sum = 0
        sch_sum = 0
        sem_sum = 0
        count = 0

        with open(bench_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                lex_sum += 1 if data.get("lexical_has") else 0
                sch_sum += 1 if data.get("schema_has") else 0
                sem_sum += 1 if data.get("semantic_has") else 0
                count += 1

        if count > 0:
            metrics["lexical_has"] = (lex_sum / count) * 100
            metrics["schema_has"] = (sch_sum / count) * 100
            metrics["semantic_has"] = (sem_sum / count) * 100
            metrics["total_files"] = count
    except (json.JSONDecodeError, OSError, IOError):
        pass
    return metrics


def get_dir_size(path: Path) -> int:
    """Calculates total size of a directory in bytes."""
    total = 0
    try:
        if path.exists():
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
    except OSError:
        pass
    return total


def format_size(bytes: int) -> str:
    """Formats bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"


def handle_status_command(args, engine, console):
    """Displays the Yamlr SRE Dashboard."""
    # [Zero-Blindspot] Stability Gate
    from yamlr.core.entrypoints.base import verify_stability_consent

    if not verify_stability_consent(args.kube_version, args):
        return 1

    workspace = engine.workspace
    target_version = engine.cluster_version
    app_name = engine.app_name

    # 1. Data Collection
    from yamlr.core.license_manager import LicenseManager
    from yamlr.core.pro.usage_limiter import UsageLimiter

    status_pro, _ = LicenseManager.check_pro_status()
    caps = LicenseManager.resolve_capabilities()
    remaining = UsageLimiter.get_remaining_quota()

    state_dir = workspace / f".{app_name}"
    backup_dir = state_dir / "backups"
    backup_size = get_dir_size(backup_dir)
    backup_count = sum(1 for _ in backup_dir.rglob("*") if _.is_file()) if backup_dir.exists() else 0

    cm = CatalogManager()
    catalog_path = cm.resolve_catalog(target_version, auto_fetch=False)
    catalog_exists = os.path.exists(catalog_path)

    has_local_config = (workspace / ".yamlr.yaml").exists() or (workspace / ".yamlr.yml").exists()
    has_metrics = get_bench_metrics(workspace)

    # 2. JSON Output
    if getattr(args, "output", "text") == "json":
        stats = engine.telemetry.get_stats() if hasattr(engine, "telemetry") and engine.telemetry else {}
        dashboard_data = {
            "workspace": str(workspace),
            "engine_tier": "Enterprise" if status_pro.is_usable() else "Standard",
            "pro_activation_status": status_pro.value,
            "capabilities": [k.replace("can_", "") for k, v in caps.__dict__.items() if v and k.startswith("can_")],
            "quota": {"remaining": remaining, "is_unlimited": remaining == 999999},
            "performance": {
                "peak_fps": stats.get("peak_throughput_fps", 0.0),
                "avg_latency_ms": stats.get("avg_latency_ms", 0.0),
                "total_heals": stats.get("total_heals", 0),
                "time_saved_hours": round(stats.get("total_time_saved_minutes", 0) / 60.0, 2),
            },
            "system": {
                "backup_size_bytes": backup_size,
                "backup_count": backup_count,
                "catalog_version": str(target_version),
                "has_local_config": has_local_config,
            },
        }
        console.print_json(data=dashboard_data)
        return 0

    # 3. Text UI Render
    _render_header(console)
    _render_top_row(
        console, workspace, has_local_config, backup_size, backup_count, target_version, catalog_exists, engine
    )
    _render_quota_and_pro(console, status_pro, caps, remaining)
    _render_health_benchmarks(console, has_metrics)
    _render_onboarding_and_actions(console, workspace, has_local_config, backup_count, backup_size)
    return 0


def _render_header(console):
    title = Text("Yamlr System Reliability Engineering (SRE) Dashboard", style="bold cyan", justify="center")
    console.print(
        Panel(title, border_style="cyan", box=box.ROUNDED if not getattr(console, "_yamlr_plain", False) else box.ASCII)
    )
    console.print()


def _render_top_row(console, workspace, has_local, b_size, b_count, version, cat_exists, engine):
    w_table = Table(show_header=False, box=None, padding=(0, 2))
    w_table.add_column(style=BOLD_WHITE)
    w_table.add_column()
    w_table.add_row("Workspace", f"[cyan]{escape(str(workspace))}[/cyan]")
    w_table.add_row("Config State", "[green]Loaded[/green]" if has_local else "[yellow]Default[/yellow]")
    w_table.add_row("Backup Vault", f"{format_size(b_size)} ({b_count} files)")
    w_table.add_row(
        "Catalog", f"{version} [green](Healthy)[/green]" if cat_exists else f"{version} [red](Update Required)[/red]"
    )
    w_panel = Panel(w_table, title="[bold cyan]🌍 Workspace Health[/bold cyan]", border_style="cyan", padding=(1, 2))

    e_table = Table(show_header=False, box=None, padding=(0, 2))
    e_table.add_column(style=BOLD_WHITE)
    e_table.add_column()
    if hasattr(engine, "telemetry") and engine.telemetry:
        stats = engine.telemetry.get_stats()
        fixed = stats.get("total_fixed_issues", 0)
        saved = stats.get("total_time_saved_minutes", 0)
        fps = stats.get("peak_throughput_fps", 0.0)
        e_table.add_row("Issues Healed", f"[green]{fixed:,}[/green]")
        e_table.add_row("Time Saved", f"[green]{saved / 60.0:.1f} hours[/green]")
        e_table.add_row("Peak Speed", f"[magenta]{fps:.1f} files/s[/magenta]")
    else:
        e_table.add_row("Telemetry", DIM_NA)
    e_panel = Panel(
        e_table, title="[bold magenta]⚡ Engine Telemetry[/bold magenta]", border_style="magenta", padding=(1, 2)
    )

    grid = Table.grid(expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(w_panel, e_panel)
    console.print(grid)


def _render_quota_and_pro(console, status_pro, caps, remaining):
    q_table = Table(show_header=False, box=None, padding=(0, 2))
    q_table.add_column(style=BOLD_WHITE)
    q_table.add_column()

    q_table.add_row(
        "Pro Status",
        f"[bold green]{status_pro.name}[/bold green]"
        if status_pro.is_usable()
        else f"[yellow]{status_pro.name}[/yellow]",
    )
    if remaining != 999999:
        q_table.add_row("Daily Quota", f"[bold cyan]{remaining}[/bold cyan] heals remaining today")
    else:
        q_table.add_row("Daily Quota", "[bold green]Unlimited[/bold green] (Pro Active)")

    active_caps = [
        k.replace("can_", "").replace("_", " ").title() for k, v in caps.__dict__.items() if v and k.startswith("can_")
    ]
    q_table.add_row("Capabilities", ", ".join(active_caps[:3]) + ("..." if len(active_caps) > 3 else ""))

    q_panel = Panel(
        q_table, title=f"[{BOLD_YELLOW}]💎 License & Quota[/{BOLD_YELLOW}]", border_style="yellow", padding=(1, 2)
    )
    console.print(q_panel)


def _render_health_benchmarks(console, has_metrics):
    if has_metrics["total_files"] == 0:
        return
    h_table = Table(show_header=True, box=box.SIMPLE_HEAD, header_style=BOLD_YELLOW, expand=True)
    h_table.add_column("Sub-System")
    h_table.add_column("Score", justify="right")
    h_table.add_row("Lexical Integrity", f"{has_metrics['lexical_has']:.1f}%")
    h_table.add_row("Schema Compliance", f"{has_metrics['schema_has']:.1f}%")
    h_table.add_row("Logical Referentiality", f"{has_metrics['semantic_has']:.1f}%")
    console.print(Panel(h_table, title=f"[{BOLD_YELLOW}]🔬 Health Benchmarks[/{BOLD_YELLOW}]", border_style="yellow"))


def _render_onboarding_and_actions(console, workspace, has_local, b_count, b_size):
    checklist = {
        "Config Loaded": has_local,
        "First Scan": b_count > 0,
        "Demo Explored": (workspace / "yamlr-demo").exists(),
    }
    b_table = Table(show_header=False, box=None, padding=(0, 4))
    for item, done in checklist.items():
        b_table.add_row(item, "[green]✅[/green]" if done else "[red]⭕[/red]")
    console.print(Panel(b_table, title="[bold blue]🚀 Onboarding[/bold blue]", border_style="blue"))

    if b_size > 100 * 1024 * 1024:
        console.print("\n[yellow]⚠️  Notice:[/yellow] Backup vault is large (>100MB).")
    if not has_local:
        console.print("\n[bold magenta]Next Step:[/bold magenta] Run [cyan bold]yamlr init[/cyan bold]")
