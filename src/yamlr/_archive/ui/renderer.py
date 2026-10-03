"""Terminal rendering components and rich formatting for Yamlr CLI output."""

import time
from typing import Any, Dict, List, Optional

from rich import box
from rich.columns import Columns
from rich.live import Live
from rich.panel import Panel
from rich.progress import ProgressBar
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from yamlr.ui.diff_engine import SideBySideDiff
from yamlr.ui.theme import (
    COLOR_ERROR,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    ICON_ALERT,
    ICON_HEAL,
    ICON_INTEGRITY,
    ICON_PRO,
    ICON_SCAN,
    ICON_SUCCESS,
    STYLE_PRIMARY,
    STYLE_SECONDARY,
    STYLE_SUCCESS,
    console,
)

STYLE_BOLD_CYAN = STYLE_SECONDARY
STYLE_BOLD_MAGENTA = STYLE_PRIMARY

class RichRenderer:
    """The 'Engine Grade' UI rendering engine for Yamlr."""

    @staticmethod
    def render_welcome(workspace_path: str, k8s_version: str, is_verified: bool = False):
        """Displays a minimalist, high-fidelity entry dashboard."""
        # 1. Minimalist Marker
        console.print("\n[bold white]Yamlr[/bold white] [dim]•[/dim] [blue]The Kubernetes Integrity Engine[/blue] [dim]v0.1.0[/dim]\n")
        
        # 2. Workspace Dashboard
        status = "[bold green]Healthy (Verified)[/bold green]" if is_verified else "Checking..."
        
        table = Table.grid(padding=(0, 2))
        table.add_row("[dim]Workspace:[/dim]", f"[bold]{workspace_path}[/bold]")
        table.add_row("[dim]Intelligence:[/dim]", f"[bold]v{k8s_version} (Standard)[/bold]")
        table.add_row("[dim]Status:[/dim]", f"{status}")
        
        console.print(table)
        console.print("\n[dim]Run 'yamlr --help' for the command reference.[/dim]\n")

    @staticmethod
    def render_explain(query: str, data: Optional[Dict[str, str]]):
        """Displays a context-aware technical explanation panel."""
        if data:
            RichRenderer.render_technical_dossier(query, data)
        else:
            # Check if it's a K8s field (e.g. deployment.spec)
            if "." in query:
                RichRenderer.render_k8s_field_dossier(query)
            else:
                console.print(f"\n[bold red]Error:[/bold red] No forensic data found for [yellow]'{query}'[/yellow].")
                console.print("[dim]Try: 'discovery', 'Y-101', 'scan', or 'Deployment'.[/dim]")

    @staticmethod
    def render_technical_dossier(query: str, data: Dict[str, str]):
        """Renders a high-density technical dossier."""
        table = Table.grid(padding=(1, 2))
        table.add_column(style=STYLE_BOLD_CYAN, width=15)
        table.add_column()

        table.add_row("CONCEPT", data.get("title", query.upper()))
        table.add_row("DEFINITION", data.get("definition", "N/A"))
        table.add_row("SRE RATIONALE", f"[italic]{data.get('rationale', 'N/A')}[/italic]")
        table.add_row("ROI IMPACT", f"[bold green]{data.get('impact', 'N/A')}[/bold green]")
        
        if "example" in data:
            table.add_row("EXAMPLE", f"[dim]{data['example']}[/dim]")

        console.print(Panel(
            table,
            title=f"[bold]{ICON_INTEGRITY} Yamlr Technical Authority[/bold]",
            subtitle="[dim]Standard: Yamlr Integrity Engine[/dim]",
            border_style="dim",
            padding=(1, 2)
        ))

    @staticmethod
    def render_k8s_field_dossier(field_path: str):
        """Renders a dossier for a native K8s field."""
        # Note: In a full implementation, this would query yamlr_native.native_get_schema
        console.print(Panel(
            f"Forensic lookup for native field: [bold green]{field_path}[/bold green]\n\n"
            "[italic]Yamlr is currently analyzing the schema registry for this field...[/italic]\n"
            "[dim]Note: Field-level explain is coming in the next build.[/dim]",
            title=f"[{STYLE_BOLD_CYAN}]Native Registry Discovery[/{STYLE_BOLD_CYAN}]",
            border_style="cyan"
        ))

    @staticmethod
    def animate_integrity_scan(old_score: float, new_score: float):
        """Animates an integrity scan progress bar (Professional standard)."""
        if new_score <= old_score and new_score < 100:
            return

        console.print(f"\n[{STYLE_SECONDARY}]{ICON_INTEGRITY} Workspace Integrity Scan[/{STYLE_SECONDARY}]")
        
        with Live(console=console, refresh_per_second=10) as live:
            target = int(new_score)
            start = int(old_score) if old_score < target else 0
            
            for i in range(start, target + 1):
                if i > 80:
                    color = "green"
                elif i > 50:
                    color = "yellow"
                else:
                    color = "red"
                    
                bar = ProgressBar(total=100, completed=i, width=40, style=color)
                renderable = Columns([
                    bar, 
                    Text(f" {i}%", style=f"bold {color}")
                ])
                live.update(renderable)
                time.sleep(0.02)
        
        if new_score > old_score:
            console.print(f"  [bold green]⬆ Workspace integrity improved by {int(new_score - old_score)}%![/bold green]")
        elif new_score == 100:
            console.print(f"  [bold cyan]{ICON_SUCCESS} Integrity Verified: Workspace is at 100% standard.[/bold cyan]")

    @staticmethod
    def render_summary(stats: Dict[str, Any]):
        """Renders a minimalist high-density batch execution summary."""
        table = Table(box=box.SIMPLE, header_style=STYLE_SECONDARY)
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")
        
        table.add_row("Files Processed", str(stats.get("total_files", 0)))
        table.add_row("Verified Assets", f"[{COLOR_SUCCESS}]{stats.get('verified', 0)}[/{COLOR_SUCCESS}]")
        table.add_row("Violations Found", f"[{COLOR_ERROR}]{stats.get('violations', 0)}[/{COLOR_ERROR}]")
        table.add_row("Auto-Healed", f"[{COLOR_SUCCESS}]{stats.get('healed', 0)}[/{COLOR_SUCCESS}]")
        table.add_row("Execution Time", f"{stats.get('time_ms', 0)}ms")
        
        console.print("\n")
        console.print(table)
        console.print("\n")
        
        if stats.get("pro_fixable", 0) > 0:
            console.print(Panel(
                f"[bold #875fff]{ICON_PRO} There are {stats['pro_fixable']} additional issues that can be fixed with Yamlr PRO.[/bold #875fff]\n"
                "[dim]Upgrade at: https://yamlr.dev/pro[/dim]",
                title="[yellow]UNLOCK ENTERPRISE HEALING[/yellow]",
                border_style="cyan",
                expand=False
            ))
        
        # Smart Tip Logic
        if stats.get("violations", 0) > 0:
            console.print(Panel(
                "Issues detected in batch. To investigate:\n"
                f"[{STYLE_BOLD_CYAN}]yamlr explain <error_code>[/{STYLE_BOLD_CYAN}]\n"
                "To automatically heal, run:\n"
                f"[{STYLE_BOLD_CYAN}]yamlr heal . --apply[/{STYLE_BOLD_CYAN}]",
                title="[yellow]TIP: SMART TIP[/yellow]",
                border_style="yellow",
                expand=False
            ))

    @staticmethod
    def render_precision_help(categories: Dict[str, List[Dict[str, str]]], show_all: bool = False):
        """Displays a categorized, high-fidelity command reference."""
        console.print("\n[bold white]Yamlr[/bold white] [dim]•[/dim] [blue]Command Reference[/blue] [dim]v0.1.0[/dim]\n")
        
        display_categories = categories.keys() if show_all else ["Basic Commands (Core)"]
        
        for category in display_categories:
            commands = categories.get(category, [])
            if not commands: continue
            
            table = Table(box=box.SIMPLE, header_style=STYLE_SECONDARY, title=f"[bold]{category}[/bold]", title_justify="left")
            table.add_column("Command", style=STYLE_PRIMARY, width=15)
            table.add_column("Purpose")
            
            for cmd in commands:
                table.add_row(cmd["name"], cmd["purpose"])
                
            console.print(table)
        
        if not show_all:
            console.print("[dim]Run 'yamlr --help --all' to inspect all commands across Intelligence, Advanced, and Ecosystem.[/dim]")
        console.print("[dim]Run 'yamlr COMMAND --help' or 'yamlr help COMMAND' for flag-level precision.[/dim]\n")

    @staticmethod
    def render_breadcrumb(command: str):
        """Displays a proactive discovery tip (Breadcrumb Strategy)."""
        tips = {
            "scan": "Pro Tip: Run 'yamlr dna' to generate immutable integrity receipts for these assets.",
            "heal": "Pro Tip: Run 'yamlr roi' to see the total risk and toil mitigated by this session.",
            "status": "Pro Tip: Run 'yamlr drift' to reconcile your live cluster state against this workspace.",
            "dna": "Pro Tip: Run 'yamlr verify' to securely validate these receipts against the registry.",
        }
        
        tip = tips.get(command)
        if tip:
            console.print(f"\n[dim]{tip}[/dim]\n")

    @staticmethod
    def render_graph(edges: List[Any], blast_radius: Optional[Any] = None):
        """Renders a minimalist topological tree of resource dependencies."""
        console.print(f"\n[{STYLE_SECONDARY}]Yamlr Topology Graph: Relational Discovery[/{STYLE_SECONDARY}]")
        
        # Simple adjacency list
        adj = {}
        for e in edges:
            adj.setdefault(e.source, []).append((e.target, e.edge_type))
            
        # Find roots (nodes with no incoming edges or just picked arbitrarily for display)
        all_targets = {e.target for e in edges}
        roots = {e.source for e in edges if e.source not in all_targets}
        if not roots and edges:
            roots = {edges[0].source}
            
        for root in sorted(roots):
            tree = Tree(f"[{COLOR_PRIMARY}]{root}[/{COLOR_PRIMARY}]")
            visited = {root}
            RichRenderer._build_rich_tree(tree, root, adj, visited)
            console.print(tree)
            
        if blast_radius:
            console.print(f"\n[bold red][!] Blast Radius: {blast_radius.source}[/bold red]")
            console.print(f"  - Affected Resources: [bold yellow]{blast_radius.affected_count}[/bold yellow]")
            console.print(f"  - Max Impact Depth:   [bold yellow]{blast_radius.depth}[/bold yellow]")
            console.print(f"  - Global Risk Level:  [bold red]{blast_radius.risk_level}[/bold red]")

    @staticmethod
    def _build_rich_tree(tree, node, adj, visited):
        if node in adj:
            for target, edge_type in adj[node]:
                if target not in visited:
                    visited.add(target)
                    branch = tree.add(f"[dim]({edge_type})[/dim] [cyan]{target}[/cyan]")
                    RichRenderer._build_rich_tree(branch, target, adj, visited)
    @staticmethod
    def render_integrity_ring(score: float):
        """Displays a health health ring for manifest integrity."""
        if score > 90:
            color = "green"
        elif score > 70:
            color = "yellow"
        else:
            color = "red"

        panel = Panel(
            Text(f"{int(score)}%", style=f"bold {color} size=20"),
            title="[bold]Integrity Score[/bold]",
            border_style=color,
            padding=(1, 2),
            expand=False
        )
        console.print(panel)

    @staticmethod
    def render_side_by_side_diff(old_content: str, new_content: str, title: str = "Manifest Side-by-Side Diff"):
        """Renders a two-column side-by-side diff table using diff_engine."""
        from yamlr.ui.diff_engine import render_side_by_side_diff
        render_side_by_side_diff(old_content, new_content, title=title)

    @staticmethod
    def render_batch_summary(report, apply: bool):
        """Renders a summary table of scan/heal results across all files.

        Args:
            report: NativeReport object with results and timing.
            apply: Whether healing was applied.
        """
        total_violations = 0
        total_integrity = 0
        healthy_count = 0

        for res in report.results:
            v_count = len(res.violations) if hasattr(res, 'violations') else 0
            i_count = len(res.integrity_violations) if hasattr(res, 'integrity_violations') else 0
            total_violations += v_count
            total_integrity += i_count
            if v_count == 0 and i_count == 0:
                healthy_count += 1

        table = Table(title="Batch Summary", show_header=True, box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white", justify="right")

        table.add_row("Files Scanned", str(report.total_files))
        table.add_row("Healthy", f"[green]{healthy_count}[/green]")
        table.add_row("Schema Violations", f"[yellow]{total_violations}[/yellow]" if total_violations else "[green]0[/green]")
        table.add_row("Integrity Issues", f"[red]{total_integrity}[/red]" if total_integrity else "[green]0[/green]")
        table.add_row("Mode", "[bold green]Heal (Applied)[/bold green]" if apply else "[dim]Scan Only[/dim]")
        table.add_row("Time", f"{report.total_time_ms}ms")

        console.print(table)

    @staticmethod
    def render_score_animation(report):
        """Displays an animated integrity score based on scan results.

        Args:
            report: NativeReport object with per-file health scores.
        """
        if not report.results:
            return

        scores = [
            res.health_score for res in report.results
            if hasattr(res, 'health_score')
        ]
        if not scores:
            return

        avg_score = sum(scores) / len(scores)

        # Animate from 0 to final score
        steps = 20
        for i in range(steps + 1):
            current = (avg_score / steps) * i
            bar_filled = int(current / 5)
            bar_empty = 20 - bar_filled

            if current > 90:
                color = "green"
            elif current > 70:
                color = "yellow"
            else:
                color = "red"

            bar = f"[{color}]{'#' * bar_filled}[/{color}][dim]{'.' * bar_empty}[/dim]"
            console.print(f"\r  Integrity: {bar} {current:.0f}%", end="")
            time.sleep(0.02)

        console.print()  # Final newline
        RichRenderer.render_integrity_ring(avg_score)

    @staticmethod
    def render_unified_diff(old_content: str, new_content: str, title: str = "Manifest Unified Diff"):
        """Renders a unified diff using diff_engine."""
        from yamlr.ui.diff_engine import render_unified_diff
        render_unified_diff(old_content, new_content, title=title)

    @staticmethod
    def render_drift_report(drifts: List[str]):
        """Renders a specialized architectural drift report."""
        console.print(f"\n[{STYLE_SECONDARY}]{ICON_INTEGRITY} Architectural Drift Discovery[/{STYLE_SECONDARY}]")
        
        if not drifts:
            console.print(f"  [bold green]{ICON_SUCCESS} No version drift detected across the workspace.[/bold green]\n")
            return

        table = Table(box=box.SIMPLE, header_style=STYLE_SECONDARY)
        table.add_column("Resource Identifier", style=STYLE_PRIMARY)
        table.add_column("Violation Detail")
        
        for drift in drifts:
            # Parse "Resource 'X' is defined with multiple API versions: A and B."
            # Heuristic parsing for the table
            parts = drift.split("'")
            resource = parts[1] if len(parts) > 1 else "Unknown"
            detail = drift.replace(f"Resource '{resource}' ", "")
            table.add_row(resource, detail)
            
        console.print(table)
        console.print(f"\n[bold yellow][!] {len(drifts)} drift hazards detected.[/bold yellow]")
        console.print("[dim]Action: Reconcile these manifests to a single API version to prevent deployment collisions.[/dim]\n")

    @staticmethod
    def render_audit_report(findings: List[Dict[str, Any]]):
        """Renders a specialized forensic audit report covering multiple hazard categories."""
        console.print(f"\n[{STYLE_SECONDARY}]{ICON_ALERT} Cross-Resource Forensic Audit[/{STYLE_SECONDARY}]")
        
        if not findings:
            console.print(f"  [bold green]{ICON_SUCCESS} No forensic hazards found. Cluster topology is healthy.[/bold green]\n")
            return

        table = Table(box=box.ROUNDED, border_style="dim", header_style="bold cyan")
        table.add_column("Severity", width=12)
        table.add_column("Hazard Category", width=25)
        table.add_column("Description", style="dim")

        for f in findings:
            sev = f.get("sev", "INFO")
            color = "red" if sev == "CRITICAL" else "yellow" if sev == "WARNING" else "dim"
            table.add_row(
                f"[bold {color}]{sev}[/bold {color}]",
                f.get("type", "Forensic Event"),
                f.get("msg", "")
            )
            
        console.print(table)
        
        critical_count = len([f for f in findings if f.get("sev") == "CRITICAL"])
        if critical_count > 0:
            console.print(f"\n[bold red][!] {critical_count} critical topology hazards detected.[/bold red]")
            console.print("[dim]Note: Critical hazards must be remediated to prevent cascading fleet-wide outages.[/dim]\n")
        else:
            console.print(f"\n[bold yellow][!] {len(findings)} forensic events identified.[/bold yellow]\n")

    @staticmethod
    def render_inline_word_diff(old_content: str, new_content: str, title: str = "Manifest Mutation Preview"):
        """Renders an inline token-level word diff using diff_engine."""
        from yamlr.ui.diff_engine import render_inline_diff
        render_inline_diff(old_content, new_content, title=title)

