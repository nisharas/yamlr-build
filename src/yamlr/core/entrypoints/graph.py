"""
Yamlr GRAPH ENTRYPOINT
-----------------------
Handles the 'yamlr graph' command and its subcommands.

Why: Decouples CLI orchestration from visual rendering and graph logic.
"""

from __future__ import annotations
import logging
from typing import Any
from rich.console import Console

from yamlr.ui.graph_renderer import GraphRenderer

logger = logging.getLogger("yamlr.entrypoints.graph")

def handle_graph_command(args: Any, engine: Any, console: Console) -> int:
    """Entry point for all graph-related actions."""
    action = getattr(args, "action", "topo")
    
    # 1. Build the Resource Graph (Zero-Latency)
    # Why: We reuse batch_heal in dry-run mode to populate the graph without mutations.
    results = engine.batch_heal(args.path, dry_run=True)
    
    # Aggregate identities from all results
    all_identities = []
    for res in results:
        all_identities.extend(getattr(res, "_raw_identities", []))

    from yamlr.core.resource_graph import ResourceGraph
    graph = ResourceGraph()
    graph.build(all_identities)
    
    renderer = GraphRenderer(console)
    
    if action == "topo":
        renderer.render_topo(graph)
        return 0
        
    elif action == "export":
        fmt = getattr(args, "format", "mermaid")
        if fmt == "mermaid":
            mermaid_spec = renderer.render_mermaid(graph)
            console.print(mermaid_spec)
        elif fmt == "json":
            import json
            console.print(json.dumps(graph.to_dict(), indent=2))
        else:
            console.print(f"[red]Format '{fmt}' is not yet supported in this version.[/red]")
            return 1
        return 0
        
    elif action == "blast-radius":
        resource_key = getattr(args, "resource", "")
        if not resource_key:
            console.print("[red]Missing required --resource <kind/name>[/red]")
            return 1
            
        # [PHASE-1.2] Blast Radius logic
        # Directly leverage ResourceGraph recursive dependency/dependent resolution
        nodes = graph.get_all_nodes()
        target_node = next((n for n in nodes if n.key == resource_key or f"{n.kind}/{n.name}" == resource_key), None)
        
        if not target_node:
            console.print(f"[red]Resource '{resource_key}' not found in the current graph.[/red]")
            return 1
            
        console.print(f"[bold cyan]💥 Blast Radius Analysis: {target_node.kind}/{target_node.name}[/bold cyan]")
        
        # 1. Upstream (What depends on this? Impact of change)
        dependents = graph.dependents(target_node.key)
        if dependents:
            console.print("\n[bold yellow]Upstream Impact (Dependents):[/bold yellow]")
            for dep in sorted(dependents, key=lambda x: x.key):
                console.print(f"  • [bold]{dep.kind}[/bold]/{dep.name}")
        else:
            console.print("\n[dim]No upstream dependents found.[/dim]")
            
        # 2. Downstream (What does this depend on? Cause of failure)
        dependencies = graph.dependencies(target_node.key)
        if dependencies:
            console.print("\n[bold blue]Downstream Requirements (Dependencies):[/bold blue]")
            for dep in sorted(dependencies, key=lambda x: x.key):
                console.print(f"  • [bold]{dep.kind}[/bold]/{dep.name}")
        else:
            console.print("\n[dim]No downstream dependencies found.[/dim]")
            
        return 0
        
    else:
        console.print(f"[red]Unknown graph action: {action}[/red]")
        return 1
