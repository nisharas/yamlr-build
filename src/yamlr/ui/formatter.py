#!/usr/bin/env python3
"""
Yamlr FORMATTER - The Visual Heart
-----------------------------------
Renders high-fidelity surgical reports using 'rich'.
Supports multi-doc expansion, staged audit logs, and unified diffs.

Modularity:
Decomposed into focused mixins (formatter_report, formatter_batch)
per the <500 line modularity rule. This file serves as the coordinator,
retaining __init__, shared utilities, and backward-compatible re-exports.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-01-26
Version: 1.1.0 (Modular Decomposition)
"""

from typing import Any, Dict, List
from rich.panel import Panel
from rich.table import Table

from yamlr.ui.formatter_report import ReportMixin, get_score_emoji
from yamlr.ui.formatter_batch import BatchMixin
from yamlr.ui.formatter_summary import SummaryMixin
from yamlr.ui.formatter_bench import BenchMixin
from yamlr.cli.commands.base import get_console

console = get_console()

# Re-export get_score_emoji at module level for backward compatibility
__all__ = ["YamlrFormatter", "get_score_emoji"]


class YamlrFormatter(ReportMixin, BatchMixin, SummaryMixin, BenchMixin):
    """
    Renders surgical reports with multi-doc awareness and staged log hierarchy.

    Now supports summary-only mode for batch operations at scale.

    Mixins:
    - ReportMixin: Single-file report display, issues summary, audit trails
    - BatchMixin: Batch summary tables (detailed + compact CI/CD mode)
    """

    def __init__(self):
        """Initialize formatter with no configuration needed."""
        pass

    # -------------------------------------------------------------------------
    # Shared Utilities (Used by both ReportMixin and BatchMixin)
    # -------------------------------------------------------------------------

    def display_error(self, file_path: str, error_msg: str, status: str = "ERROR"):
        """Displays a formatted error panel."""
        panel = Panel(
            f"[red]{error_msg}[/red]",
            title=f"[bold red]❌ {status}: {file_path}[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
        console.print(panel)

    def _render_deprecation_summary(self, reports: List[Any]):
        """Renders an aggregate table of API deprecations found in the batch."""
        deprecations = {}

        for r in reports:
            # Handle both dict and object (HealResult)
            identities = []
            if isinstance(r, dict):
                identities = r.get("identities", [])
            elif hasattr(r, "identities"):
                identities = r.identities

            for identity in identities:
                # Handle both dict and ManifestIdentity object
                dep = None
                kind = "Unknown"
                if isinstance(identity, dict):
                    dep = identity.get("deprecation_info")
                    kind = identity.get("kind", "Unknown")
                else:
                    dep = getattr(identity, "deprecation_info", None)
                    kind = getattr(identity, "kind", "Unknown")

                if dep:
                    # Logic to extract sig from dep (can be dict or object)
                    if isinstance(dep, dict):
                        sig = (
                            kind,
                            dep.get("deprecated_api", "?"),
                            dep.get("replacement_api", "?"),
                            dep.get("removed_in_version", "?"),
                        )
                    else:
                        sig = (
                            kind,
                            getattr(dep, "deprecated_api", "?"),
                            getattr(dep, "replacement_api", "?"),
                            getattr(dep, "removed_in_version", "?"),
                        )
                    deprecations[sig] = deprecations.get(sig, 0) + 1

        if not deprecations:
            return

        table = Table(
            title="\n[bold yellow]⚠️  API Deprecation Summary[/bold yellow]",
            show_header=True,
            header_style="bold yellow",
            expand=True,
            box=None,
        )
        table.add_column("Resource Kind", style="cyan")
        table.add_column("Deprecated API", style="red")
        table.add_column("Replacement", style="green")
        table.add_column("Removed In", style="bold red")
        table.add_column("Count", justify="center")

        # Sort alphabetically by kind then old API to guarantee determinism
        for (kind, old, new, removed), count in sorted(deprecations.items(), key=lambda x: (x[0][0], x[0][1])):
            table.add_row(kind, old, new, removed, str(count))

        console.print(table)
