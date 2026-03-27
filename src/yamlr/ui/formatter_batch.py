#!/usr/bin/env python3
"""
Formatter BATCH Mixin
---------------------
Multi-file batch summary tables: detailed per-resource rows and compact CI/CD mode.

Why: Extracted from formatter.py to enforce the <500 line modularity rule.
This mixin provides batch display methods that YamlrFormatter inherits.

Architecture: Mixin pattern — shares state via `self` with the main class.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-17
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from yamlr.models import HealFileResult

from rich.panel import Panel
from rich.table import Table

from yamlr.cli.commands.base import get_console

console = get_console()
__all__ = ['BatchMixin']



class BatchMixin:
    """
    Batch summary table methods for YamlrFormatter.

    Responsibilities:
    - Summary table routing (detailed vs compact)
    - Detailed per-file/per-resource table
    - Compact CI/CD summary stats
    """

    PRO_FIXABLE_RULES = {
        "rule/resource-requests", "rule/resource-limits",
        "rule/run-as-non-root", "rule/no-privileged", "rule/allow-privilege-escalation",
        "rule/unsafe-hostpath", "rule/host-network", "rule/read-only-root-fs",
        "rule/missing-liveness", "rule/missing-readiness",
        "rule/no-latest-tag",
        "rule/ghost-service", "rule/port-mismatch", "rule/service-no-selector",
        "rule/missing-configmap-target", "rule/broken-volume", "rule/ingress-broken",
        "rule/network-policy-missing", "rule/untrusted-registry"
    }

    # -------------------------------------------------------------------------
    # Multi-Doc Expanded Summary Table
    # -------------------------------------------------------------------------

    def print_final_table(
        self, reports: List[HealFileResult], summary_only: bool = False, telemetry_data: Optional[Dict[str, Any]] = None, **kwargs
    ):
        """
        Summary table with multi-resource expansion.
        
        Why: Orchestrates the final visual output after a batch operation.
             Decoupled to support both detailed inspection and high-level 
             ROI summaries.
             
        Args:
            reports: List of file processing results
            summary_only: If True, show aggregate stats only (recommended for 100+ files)
            telemetry_data: Optional persistent stats from TelemetryManager
        """
        if not reports:
            console.print("[dim yellow]No files processed.[/dim yellow]")
            return

        # FIX: For large batches, use summary mode
        if summary_only or len(reports) > 5:
            # Note: caller should pass elapsed_time if available
            elapsed_time = kwargs.get("elapsed_time", 0.0)
            console.print(
                f"\n[dim]Processed {len(reports)} files - using summary mode[/dim]\n"
            )
            self._print_summary_stats(reports, elapsed_time=elapsed_time, telemetry_data=telemetry_data)
            return

        # Standard detailed table for smaller batches
        self._print_detailed_table(reports)

    def _get_icon(self, icon: str) -> str:
        """Returns ASCII fallback for emojis if plain mode is active.
        
        Why: Ensures terminal compatibility and accessibility for users 
             with no-color or basic TTY environments.
        """
        if not getattr(console, "_yamlr_plain", False):
            return icon
        
        mapping = {
            "📊": "[#]", "✅": "[v]", "✓": "v", "→": "->", 
            "✎": "*", "⚠": "!", "○": "o", "↪": ">>", "✗": "x",
            "💾": "(B)", "✨": "OK", "💡": "i", "⚔️": "[!]"
        }
        return mapping.get(icon, icon)

    def _print_detailed_table(self, reports: List[HealFileResult]):
        """Renders detailed table with per-file and per-resource rows.
        
        Why: Provides the 'Surgical Precision' view, allowing users to trace 
             exactly what was found and healed in each manifest.
        """
        table = Table(
            title="\n[bold magenta]━━━ Yamlr Healing Summary ━━━[/bold magenta]",
            show_header=True,
            header_style="bold white on magenta",
            show_lines=True,
            padding=(0, 1),
        )

        table.add_column("File / Resource", style="cyan", no_wrap=False)
        table.add_column("Kind/Name", justify="left")
        table.add_column("Score", justify="center", width=8)
        table.add_column("Time", justify="right", width=8)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Issues", justify="center", width=10)
        table.add_column("✓", justify="center", width=3)

        total_files = len(reports)
        successful = 0
        healed = 0
        unchanged = 0
        warnings = 0
        failed = 0

        for r in reports:
            status = r.get("status", "UNKNOWN")
            success = r.get("success", False)
            logs = r.get("logic_logs", [])

            # Smart Status Detection: Check for semantic warnings even if file is unchanged
            has_warnings = any("Warning" in log or "WARN" in log for log in logs)
            if status == "UNCHANGED" and has_warnings:
                status = "WARN"
            try:
                score = int(r.get("dna_integrity_score", 0))
            except (TypeError, ValueError):
                score = 0
                
            try:
                proc_time = float(r.get("processing_time_seconds", 0))
            except (TypeError, ValueError):
                proc_time = 0.0
            file_path = r.get("file_path", "Unknown")

            # Handle errors
            if status in ["ENGINE_ERROR", "FILE_NOT_FOUND", "SECURITY_ERROR"]:
                failed += 1
                table.add_row(
                    file_path,
                    f"[red]{status}[/red]",
                    "[red]0[/red]",
                    "-",
                    "[bold red]ERROR[/bold red]",
                    "1 Error",
                    self._get_icon("❌"),
                )
                continue

            # Handle Skips
            if status == "SKIPPED":
                table.add_row(
                    file_path,
                    "[yellow]⚠ No K8s Identity Found[/yellow]",
                    "[dim]100[/dim]",
                    f"{proc_time:.2f}s",
                    "[bold yellow]SKIPPED[/bold yellow]",
                    "[dim](strict)[/dim]",
                    "○",
                )
                successful += 1  # A skip in strict mode is technically a success (it did what was asked)
                continue

            # Handle empty identities gracefully
            identities = r.get("identities", [])
            if not identities:
                # Show file-level row with clear message
                score_style = "yellow"
                status_style = "yellow" if status == "HEALED" else "dim yellow"
                result_icon = self._get_icon("⚠️")

                table.add_row(
                    file_path,
                    "[yellow]⚠ No K8s resources detected[/yellow]",
                    f"[{score_style}]{score}[/{score_style}]",
                    f"{proc_time:.2f}s",
                    f"[{status_style}]{status}[/{status_style}]",
                    "[dim]-[/dim]",
                    result_icon,
                )

                if status == "HEALED":
                    healed += 1
                elif status == "WARN":
                    warnings += 1
                elif status == "UNCHANGED":
                    unchanged += 1

                if success:
                    successful += 1

                continue

            # Expand resources for files with identities
            is_first_row = True
            for identity in identities:
                kind = identity.get("kind", "Unknown")
                name = identity.get("name", "unnamed")

                try:
                    score_val = int(score)
                except (TypeError, ValueError):
                    score_val = 0
                    
                score_style = (
                    "green" if score_val >= 80 else "yellow" if score_val >= 50 else "red"
                )

                if status == "HEALED":
                    status_style = "bold green"
                    if is_first_row:
                        healed += 1
                elif status == "WARN":
                    status_style = "bold yellow"
                    if is_first_row:
                        warnings += 1
                elif status == "UNCHANGED":
                    status_style = "dim green"
                    if is_first_row:
                        unchanged += 1
                elif status == "PREVIEW":
                    status_style = "yellow"
                else:
                    status_style = "dim"

                result_icon = self._get_icon("✅") if success else self._get_icon("❌")

                # Calculate issue string
                findings = r.get("findings", [])
                issue_str = "-"
                if findings:
                    errs = sum(1 for f in findings if f.get("severity") == "error")
                    warns = len(findings) - errs
                    parts = []
                    if errs:
                        parts.append(f"[red]{errs}E[/red]")
                    if warns:
                        parts.append(f"[yellow]{warns}W[/yellow]")
                    issue_str = " ".join(parts) if parts else "-"

                table.add_row(
                    file_path if is_first_row else "",
                    f"{kind}: [dim]{name}[/dim]",
                    f"[{score_style}]{score}[/{score_style}]",
                    f"{proc_time:.2f}s" if is_first_row else "",
                    f"[{status_style}]{status}[/{status_style}]"
                    if is_first_row
                    else "",
                    issue_str if is_first_row else "",
                    result_icon if is_first_row else "",
                )
                is_first_row = False

            if success:
                successful += 1

        console.print(table)

        # Summary stats
        console.print("\n[bold]Yamlr Engine Summary:[/bold]")
        console.print(
            f"  Total: {total_files} | "
            f"[green]✓ {successful}[/green] | "
            f"[cyan]→ {healed}[/cyan] | "
            f"[yellow]⚠ {warnings}[/yellow] | "
            f"[dim pink]↪ {sum(1 for r in reports if r.get('status') == 'SKIPPED')}[/dim pink] Skips | "
            f"[white]○ {unchanged}[/white] | "
            f"[red]✗ {failed}[/red]"
        )

        # [Smart UX] Show backup message ONLY if files were actually healed
        if healed > 0:
            console.print(
                f"\n[dim]{self._get_icon('💾')} {healed} backup(s) saved to .yamlr/backups/ (relative to workspace)[/dim]"
            )

        # [Smart Tip] If issues exist, guide user to single scan
        has_issues = (
            warnings > 0 or failed > 0 or any(r.get("findings") for r in reports)
        )
        if has_issues:
            console.print(
                Panel(
                    "To see the specific messages for a file listed with issues (e.g., [red]2E[/red]), "
                    "you should run a standard scan on that specific file:\n"
                    "[bold cyan]Yamlr scan <filename>[/bold cyan]\n"
                    "To preview repairs, run:\n"
                    "[bold cyan]Yamlr heal <filename> --diff[/bold cyan]",
                    title="💡 SMART TIP",
                    border_style="yellow",
                    expand=False,
                )
            )
        console.print()

        # [Feature] Deprecation Summary
        self._render_deprecation_summary(reports)

