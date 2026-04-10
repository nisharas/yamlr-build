"""
Help text for observability and strategic commands: graph, idp-export, pulse.

Why: Groups the v1.3 visual and strategic subcommand help texts as part
     of the modular help system. Part of the Observability Layer.
"""

from __future__ import annotations

__all__ = ["help_graph", "help_idp_export", "help_pulse"]


def help_graph(console, invoked_as: str) -> None:
    """Display help for the 'graph' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} graph <action>[/bold white] [options]")
    console.print("\nVisual Observability: Resource topology & blast-radius analysis.")
    console.print("\n[bold cyan]ACTIONS[/bold cyan]")
    console.print("  topo           Display ASCII tree of resource relationships")
    console.print("  export         Export graph in Mermaid or DOT format")
    console.print("  blast-radius   Analyze the impact of a specific resource")

    console.print("\n[bold cyan]OPTIONS (export)[/bold cyan]")
    console.print("  --format       Export format: mermaid (default), dot, json")

    console.print("\n[bold cyan]OPTIONS (blast-radius)[/bold cyan]")
    console.print("  --resource KEY Target resource (e.g., Deployment/my-app)")

    console.print("\n[dim]✨ Yamlr Pro provides advanced cross-resource relationship mapping.[/dim]")


def help_idp_export(console, invoked_as: str) -> None:
    """Display help for the 'idp-export' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} idp-export[/bold white] [options]")
    console.print("\nPlatform Integration: Export safety truth to Backstage or Prometheus.")
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  --format       Target format: json (default), backstage, prometheus")
    console.print("  --output-file  Write the export to a specific file instead of stdout")

    console.print("\n[dim]✨ Yamlr Pro required for native IDP and Prometheus integrations.[/dim]")


def help_pulse(console, invoked_as: str) -> None:
    """Display help for the 'pulse' command."""
    console.print(f"\n[bold green]USAGE:[/bold green] [bold white]{invoked_as} pulse[/bold white] [options]")
    console.print("\nFounder Intelligence: View aggregate rule efficacy and ecosystem ROI.")
    console.print("\n[bold cyan]OPTIONS[/bold cyan]")
    console.print("  --output json  Export pulse stats as structured JSON")

    console.print("\n[dim]✨ Strategic feature for fleet-wide visibility and due diligence.[/dim]")
