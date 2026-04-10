#!/usr/bin/env python3
"""
Yamlr Feature Discovery Engine
------------------------------
Displays a comprehensive matrix of all engine capabilities, their tiers,
and their current activation status.

Why: To ensure 100% visibility for the product roadmap and prevent 
     "Ghost Logic" blindspots during enterprise audits.
"""

from __future__ import annotations

import sys
from typing import List, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from yamlr.core.bridge import YamlrBridge
from yamlr.core.entrypoints.base import get_console

def handle_features_command(args) -> int:
    """Renders the Yamlr Capability Matrix."""
    console = get_console()
    
    is_pro = YamlrBridge.is_pro_enabled()
    status_label, _, status_color = YamlrBridge.get_pro_status_display()
    
    console.print(Panel(
        f"[bold white]Yamlr Capability Matrix[/bold white]\n"
        f"[dim]Current Tier:[/dim] [{status_color}]{status_label}[/{status_color}]",
        border_style=status_color,
        expand=False
    ))

    table = Table(box=None, header_style="bold cyan", padding=(0, 2))
    table.add_column("Category", style="dim")
    table.add_column("Capability")
    table.add_column("Tier", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Description", style="italic")

    # [FREE] Core Capabilities
    _add_feature(table, "Core", "Schema Validation", "FREE", "ACTIVE", "OpenAPI-driven K8s resource audit")
    _add_feature(table, "Core", "Visual Healing", "FREE", "ACTIVE", "Interactive, comment-preserving repair")
    _add_feature(table, "Core", "API Deprecation", "FREE", "ACTIVE", "Detecting legacy/deprecated API versions")
    _add_feature(table, "Core", "Forensic Journal", "FREE", "ACTIVE", "Atomic WAL journaling of all changes")
    
    # [FREE] Observability
    _add_feature(table, "Graph", "Relational Topology", "FREE", "ACTIVE", "ASCII tree of resource relationships")
    _add_feature(table, "Graph", "Blast Radius", "FREE", "ACTIVE", "Impact analysis for resource removal")
    
    # [SURGICAL] Free but Powerful
    _add_feature(table, "Surgical", "Auto-Injection", "FREE", "ACTIVE", "Injecting missing limits/probes/NS")
    _add_feature(table, "Surgical", "Tag Sanitization", "FREE", "ACTIVE", "Auto-remediation of :latest tags")
    _add_feature(table, "Expert", "Clinical Mode", "FREE", "ACTIVE", "Pure-YAML stdout protection for GitOps")

    # [PRO] Enterprise Capabilities
    _add_feature(table, "Sync", "Drift Remediation", "PRO", _pro_status(is_pro), "Reconcile live cluster with manifests")
    _add_feature(table, "Security", "Auto-Hardening", "PRO", _pro_status(is_pro), "Autonomous PSS-style policy injection")
    _add_feature(table, "Identity", "Semantic DNA", "PRO", _pro_status(is_pro), "SHA-256 identity for manifest integrity")
    _add_feature(table, "Compliance", "Evidence Receipts", "PRO", _pro_status(is_pro), "DNA-signed auditor-ready PDF reports")
    _add_feature(table, "Performance", "Rust Acceleration", "PRO", _pro_status(is_pro), "Native engine for hyperscale (10k+ files)")
    _add_feature(table, "Integrations", "AI Agent Bridge (MCP)", "PRO", _pro_status(is_pro), "High-fidelity healing server for LLMs")
    _add_feature(table, "Integrations", "Sovereign IDE (LSP)", "PRO", _pro_status(is_pro), "Real-time safety guard in VS Code")
    _add_feature(table, "Export", "Sovereign Sorting", "PRO", _pro_status(is_pro), "Schema-aware manifest reconstruction")

    console.print(table)
    
    if not is_pro:
        console.print(f"\n[dim]💡 Pro features are currently [yellow]Gated[/yellow]. Run [bold]yamlr auth login[/bold] to activate your enterprise license.[/dim]")
    
    return 0

def _add_feature(table: Table, category: str, name: str, tier: str, status: str, desc: str):
    tier_style = "green" if tier == "FREE" else "magenta"
    status_style = "green" if status == "ACTIVE" else "yellow"
    table.add_row(category, name, f"[{tier_style}]{tier}[/{tier_style}]", f"[{status_style}]{status}[/{status_style}]", desc)

def _pro_status(is_pro: bool) -> str:
    return "ACTIVE" if is_pro else "GATED"
