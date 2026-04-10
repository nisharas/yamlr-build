"""
RULES COMMAND - The Control Plane Dashboard
-------------------------------------------
Lists all available protections in a clean table format.
"""

from __future__ import annotations

import sys

from rich.table import Table

from yamlr.core.entrypoints.explain import RULE_DB

__all__ = ["handle_rules_command"]


SEVERITY_DISPLAY = {
    "critical": "Blocker",
    "error": "Blocker",
    "high": "Risky",
    "warning": "Warning",
    "mixed": "Warning",
    "info": "Note",
}

SEVERITY_ORDER = {
    "critical": 0,
    "error": 0,
    "high": 1,
    "warning": 2,
    "mixed": 2,
    "info": 3,
}


def display_severity(raw: str) -> str:
    """Transforms raw severity into a human-friendly display label.

    Why: To provide clear, non-technical indicators of risk levels.
    """
    return SEVERITY_DISPLAY.get(raw.lower(), raw)


def severity_rank(raw: str) -> int:
    """Returns a numeric rank for sorting rules by severity.

    Why: To ensure that the most critical risks appear first in the dashboard.
    """
    return SEVERITY_ORDER.get(raw.lower(), 99)


def handle_rules_command(args, console):
    """Displays a dashboard of all available Yamlr rules.

    Why: To provide the user with total visibility into the active safety engine.
    """
    output_fmt = getattr(args, "output", "text")

    if output_fmt == "json":
        return _handle_json_output(RULE_DB)

    console.print("\n[bold cyan]── yamlr Rule Dashboard ──[/bold cyan]\n")

    table = _setup_rules_table(getattr(args, "verbose", False))
    _populate_rules_table(table, getattr(args, "verbose", False))

    console.print(table)
    console.print(f"\n[dim]Total protections active: {len(RULE_DB)}[/dim]")
    console.print("[dim]Run 'yamlr explain <id>' for full details on any rule.[/dim]\n")

    return 0


def _handle_json_output(rule_db: dict) -> int:
    """Helper to handle JSON output for the rules command."""
    import json

    rules_data = []
    for rid, data in rule_db.items():
        rules_data.append(
            {
                "id": rid,
                "name": data.get("name", "Unknown"),
                "severity": data.get("severity", "Info"),
                "description": data.get("description", ""),
            }
        )
    sys.stdout.write(json.dumps(rules_data, indent=2) + "\n")
    return 0


def _setup_rules_table(is_verbose: bool) -> Table:
    """Helper to initialize and configure the rules table."""
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=None,
        padding=(0, 2, 0, 0),
    )
    table.add_column("Rule ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Severity")
    table.add_column("Description", style="dim white")
    if is_verbose:
        table.add_column("Rationale", style="italic green")
    return table


def _populate_rules_table(table: Table, is_verbose: bool):
    """Helper to populate the table with sorted rule data."""
    # Sort rules by severity, then name
    sorted_rules = sorted(
        RULE_DB.items(),
        key=lambda item: (
            severity_rank(item[1].get("severity", "")),
            item[1].get("name", "").lower(),
        ),
    )

    for rid, data in sorted_rules:
        raw_severity = data.get("severity", "Info")
        shown_severity = display_severity(raw_severity)
        color = _get_severity_color(raw_severity)

        description = _truncate_text(data.get("description", ""), 60)

        row_args = [
            rid,
            data.get("name", "Unknown"),
            f"[{color}]{shown_severity}[/{color}]",
            description,
        ]

        if is_verbose:
            row_args.append(_truncate_text(data.get("rationale", ""), 60))

        table.add_row(*row_args)


def _get_severity_color(raw_severity: str) -> str:
    """Maps map severity to a display color."""
    sev_l = raw_severity.lower()
    if sev_l in ("critical", "error", "high"):
        return "red"
    if sev_l in ("warning", "mixed"):
        return "yellow"
    return "white"


def _truncate_text(text: str, max_len: int) -> str:
    """Helper to truncate text with ellipsis."""
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text
