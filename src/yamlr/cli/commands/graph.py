from __future__ import annotations
from yamlr.core.resource_graph import ResourceGraph
from yamlr.ui.graph_renderer import GraphRenderer

__all__ = ["handle_graph_command"]

def handle_graph_command(args, engine, console) -> int:
    """Handles the 'yamlr graph' command suite.
    
    Why: Provides visual observability into resource dependencies and blast-radius.
    """
    action = getattr(args, "action", "topo")
    
    # 1. Build the ResourceGraph
    if not getattr(console, "_yamlr_quiet", False):
        console.print("[dim]Building resource dependency graph...[/dim]")
    
    identities = list(engine.get_all_identities())
    graph = ResourceGraph()
    graph.build(identities)
    
    renderer = GraphRenderer(console)
    
    if action == "topo":
        renderer.render_topo(graph)
    
    elif action == "export":
        fmt = getattr(args, "format", "mermaid")
        if fmt == "mermaid":
            output = renderer.render_mermaid(graph)
            console.print(output)
        else:
            console.print(f"[yellow]Format '{fmt}' not yet implemented for export. Defaulting to mermaid.[/yellow]")
            console.print(renderer.render_mermaid(graph))
            
    elif action == "blast-radius":
        res_key = getattr(args, "resource", None)
        if not res_key:
            console.print("[red]Error: --resource <kind/name> is required for blast-radius analysis.[/red]")
            return 1
            
        radius = graph.blast_radius(res_key)
        if not radius.affected_nodes:
            # Try to find node if namespace was omitted
            nodes = graph.get_all_nodes()
            matches = [n for n in nodes if f"{n.kind}/{n.name}" == res_key]
            if matches:
                radius = graph.blast_radius(matches[0].key)
            else:
                console.print(f"[red]Error: Resource '{res_key}' not found in graph.[/red]")
                return 1
        
        console.print(f"\n[bold red]💥 Blast Radius Analysis for {res_key}[/bold red]")
        console.print(f"[bold]Risk Level:[/bold] {radius.risk_level}")
        console.print(f"[bold]Impact Depth:[/bold] {radius.depth}")
        console.print(f"[bold]Resources Affected:[/bold] {len(radius.affected_nodes)}")
        
        if radius.affected_nodes:
            from rich.table import Table
            table = Table(title="Affected Resources", box=None)
            table.add_column("Kind", style="cyan")
            table.add_column("Namespace", style="yellow")
            table.add_column("Name", style="bold")
            
            for node in sorted(radius.affected_nodes, key=lambda x: (x.kind, x.name)):
                table.add_row(node.kind, node.namespace, node.name)
            console.print(table)
            
        if radius.has_ingress_impact:
            console.print("\n[bold orange3]⚠️ WARNING: Failure impacts external traffic (Ingress/Gateway).[/bold orange3]")
        if radius.has_data_impact:
            console.print("[bold orange3]⚠️ WARNING: Failure impacts persistent data or configuration.[/bold orange3]")

    return 0
