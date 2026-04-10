#!/usr/bin/env python3
"""
Yamlr BENCHMARK MIXIN
---------------------
Renders scientific benchmark reports with Multi-dimensional HAS tracking.
"""

from __future__ import annotations

from typing import Any, Dict

from rich.panel import Panel
from rich.table import Table

from yamlr.core.entrypoints.base import get_console

console = get_console()
__all__ = ["BenchMixin"]


class BenchMixin:
    """
    Mixin for YamlrFormatter to handle scientific benchmarking reports.
    """

    def print_header(self, text: str):
        """Prints a bold header.

        Why: Maintains visual hierarchy in benchmark reports.
        """
        console.print(f"\n[bold cyan]{text}[/bold cyan]")

    def print_info(self, text: str):
        """Prints dimmed information text.

        Why: Provides non-critical context without distracting from core HAS metrics.
        """
        console.print(f"[dim]{text}[/dim]")

    def print_benchmark_report(self, report: Dict[str, Any]):
        """Renders the scientific assessment dashboard.

        Why: Primary visualization for enterprise-grade performance validation,
             enabling proof of 'Healing Accuracy Score' (HAS) at scale.
        """
        # 1. Overall HAS Panel
        overall_has = report.get("overall_has", 0.0)
        color = "green" if overall_has >= 90 else "yellow" if overall_has >= 70 else "red"

        console.print(
            Panel(
                f"[bold {color}]{overall_has:.1f}%[/bold {color}]",
                title="[bold white]Overall Healing Accuracy Score (HAS)[/bold white]",
                subtitle=f"[dim]Total Manifests Processed: {report.get('total_files')}[/dim]",
                border_style=color,
                padding=(1, 4),
            )
        )

        # 2. Multi-Dimensional Category Table
        table = Table(
            title="\n[bold]📈 Category-Specific Performance (Scientific Mode)[/bold]",
            show_header=True,
            header_style="bold magenta",
            box=None,
        )
        table.add_column("Category", style="cyan", width=30)
        table.add_column("HAS", justify="right")
        table.add_column("Detect Rate", justify="right")
        table.add_column("FP Rate", justify="right")
        table.add_column("Depth (L/M/H)", justify="center")

        breakdown = report.get("category_breakdown", {})
        for name, stats in breakdown.items():
            has = stats["has"]
            has_color = "green" if has >= 90 else "red" if has < 60 else "yellow"

            depths = stats.get("depth_distribution", {})
            depth_str = f"{depths.get('Light', 0)}/{depths.get('Medium', 0)}/{depths.get('Heavy', 0)}"

            table.add_row(
                name,
                f"[{has_color}]{has:.1f}%[/{has_color}]",
                f"{stats['detection_rate']:.1f}%",
                f"{stats['fp_rate']:.1f}%",
                depth_str,
            )

        console.print(table)

        # 3. Top 10 Weakest Categories
        weakest = report.get("top_10_weakest", [])
        if weakest:
            console.print("\n[bold red]🚨 Top 10 Weakest Categories (Action Required):[/bold red]")
            for i, cat in enumerate(weakest, 1):
                console.print(f"  {i}. [yellow]{cat}[/yellow]")

        console.print("\n" + "─" * 60 + "\n")
