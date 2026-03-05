"""
RULES COMMAND - The Control Plane Dashboard
-------------------------------------------
Lists all available protections in a clean table format.
"""
from rich.table import Table
from yamlr.core.entrypoints.explain import RULE_DB


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
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    return SEVERITY_DISPLAY.get(raw.lower(), raw)


def severity_rank(raw: str) -> int:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    return SEVERITY_ORDER.get(raw.lower(), 99)


def handle_rules_command(args, console):
    """
    Displays a dashboard of all available Yamlr rules.
    """
    output_fmt = getattr(args, 'output', 'text')
    
    if output_fmt == "json":
        import json
        rules_data = []
        for rid, data in RULE_DB.items():
            rules_data.append({
                "id": rid,
                "name": data.get("name", "Unknown"),
                "severity": data.get("severity", "Info"),
                "description": data.get("description", "")
            })
        print(json.dumps(rules_data, indent=2))
        return 0

    console.print("\n[bold cyan]── yamlr Rule Dashboard ──[/bold cyan]\n")
    
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=None,
        padding=(0, 2, 0, 0),
    )
    
    is_verbose = getattr(args, 'verbose', False)
    
    table.add_column("Rule ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Severity")
    table.add_column("Description", style="dim white")
    if is_verbose:
        table.add_column("Rationale", style="italic green")
    
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

        # Color by internal severity
        sev_l = raw_severity.lower()
        color = "white"
        if sev_l in ("critical", "error"):
            color = "red"
        elif sev_l in ("high",):
            color = "red"
        elif sev_l in ("warning", "mixed"):
            color = "yellow"

        description = data.get("description", "") or ""
        if len(description) > 60:
            description = description[:60] + "..."

        row_args = [
            rid,
            data.get("name", "Unknown"),
            f"[{color}]{shown_severity}[/{color}]",
            description,
        ]
        
        if is_verbose:
            rationale = data.get("rationale", "") or ""
            if len(rationale) > 60:
                rationale = rationale[:60] + "..."
            row_args.append(rationale)

        table.add_row(*row_args)
    
    console.print(table)
    console.print(f"\n[dim]Total protections active: {len(RULE_DB)}[/dim]")
    console.print(f"[dim]Run 'yamlr explain <id>' for full details on any rule.[/dim]\n")
    
    return 0
