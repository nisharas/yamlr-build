#!/usr/bin/env python3
"""
Formatter REPORT BASE Mixin
---------------------------
Core rendering logic for file headers and identity panels.

Why: Extracted from formatter_report.py to satisfy the <500 line rule.
"""

from __future__ import annotations
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    pass

from rich.panel import Panel
from yamlr.cli.commands.base import get_console
from yamlr.ui.formatter_report_shared import get_score_emoji


class ReportBaseMixin:
    """Core rendering for file identity and header panels."""

    def _render_header_panel(self, result: Dict[str, Any], file_path: str, status: str) -> None:
        """Renders the top-level file identity and health metrics panel.
        
        Why: Provides the core identity and summary scores for the file.
        """
        try:
            score = int(result.get("dna_integrity_score", 0))
        except (TypeError, ValueError):
            score = 0
            
        color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        score_emoji = get_score_emoji(score)
        
        resources_list = [f"{i.get('kind', '?')}/{i.get('name', '?')}" for i in result.get("identities", [])]
        resources_str = ", ".join(resources_list) if resources_list else "[dim]No resources[/dim]"

        try:
            trust_score = float(result.get("trust_score", 100.0))
        except (TypeError, ValueError):
            trust_score = 100.0
            
        trust_color = "green" if trust_score >= 80 else "yellow" if trust_score >= 50 else "red"
        
        from rich import box
        box_style = getattr(get_console(), "_yamlr_box", box.ROUNDED)

        get_console().print(Panel(
            f"[bold]Resources:[/bold] {resources_str}\n"
            f"[bold]DNA Integrity:[/bold] {score_emoji} [{color}]{score}/100[/{color}]\n"
            f"[bold]Trust Score  :[/bold] [bold {trust_color}]{trust_score:.1f}%[/bold {trust_color}] (Shield Engine Hardened)\n"
            f"[bold]Status       :[/bold] {status}\n"
            f"[bold]Shield Status:[/bold] [cyan]PHY: {result.get('phy_status', '100%')}[/cyan] | [cyan]KBS: {result.get('kbs_status', '0%')}[/cyan] | [cyan]SEM: {result.get('sem_status', '0%')}[/cyan]",
            title=f"[bold {color}]Reference: {file_path}[/bold {color}]",
            border_style=color, expand=True, box=box_style,
        ))

    def _handle_early_exits(self, status: str, file_path: str, result: Dict[str, Any]) -> bool:
        """Handles SKIPPED and ERROR statuses before full report rendering."""
        if status == "SKIPPED":
            get_console().print(Panel(
                "[yellow]This file does not contain a valid Kubernetes API identity (kind + apiVersion).\nStrict Identity Mode is active, so healing was bypassed to protect your data.[/yellow]",
                title=f"[bold yellow]↪ SKIPPED: {file_path}[/bold yellow]",
                border_style="yellow", padding=(1, 2),
            ))
            return True

        if status in ["ENGINE_ERROR", "FILE_NOT_FOUND", "SECURITY_ERROR", "EMPTY_FILE"]:
            if hasattr(self, "display_error"):
                self.display_error(file_path, result.get("error", "Unknown error"), status)
            return True
        return False
