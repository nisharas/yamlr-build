"""CLI handler for schema inspection and CRD ingestion."""
import os
from typing import Any

from yamlr.core.crd_distiller import CRDDistiller
from yamlr.ui.theme import ICON_SUCCESS, console


def cmd_schema(args: Any):
    """Dispatches schema commands: ingest, list, clean."""
    action = getattr(args, "schema_action", None)
    out_val = getattr(args, "out", None)
    dir_val = getattr(args, "dir", None)
    if isinstance(out_val, str) and out_val:
        schema_dir = out_val
    elif isinstance(dir_val, str) and dir_val:
        schema_dir = dir_val
    else:
        schema_dir = ".yamlr/schemas"
    distiller = CRDDistiller(schema_dir)

    if action == "ingest":
        path = getattr(args, "path", ".")
        console.print(f"\n[bold cyan][*] Ingesting CRD schemas from:[/bold cyan] {path}")
        try:
            if os.path.isdir(path):
                compiled = distiller.distill_directory(path)
            else:
                compiled = distiller.distill_file(path)

            if compiled:
                console.print(f"[bold green]{ICON_SUCCESS} Ingested {len(compiled)} custom schema(s) into {schema_dir}[/bold green]")
                for s in compiled:
                    console.print(f"  [cyan]•[/cyan] [bold]{s['kind']}[/bold] ({s['apiVersion']}) - {len(s['fields'])} properties")
                console.print("\n[dim]Yamlr scan and heal will now validate and heal these custom resources automatically.[/dim]\n")
            else:
                console.print("[yellow][!] No CustomResourceDefinition manifests found in the specified path.[/yellow]\n")
        except Exception as e:
            console.print(f"[bold red][!] Ingestion failed:[/bold red] {e}\n")

    elif action == "list":
        console.print(f"\n[bold cyan][*] Active Custom Schemas in {schema_dir}:[/bold cyan]")
        schemas = distiller.list_schemas()
        if schemas:
            for s in schemas:
                console.print(f"  [cyan]•[/cyan] [bold]{s['kind']}[/bold] ({s['apiVersion']}) - {s['fields_count']} properties [dim]({s['file']})[/dim]")
        else:
            console.print("  [dim]No custom CRD schemas cached. Ingest with: yamlr schema ingest <crds.yaml>[/dim]")
        console.print("")

    elif action == "clean":
        count = distiller.clean_schemas()
        console.print(f"\n[bold green]{ICON_SUCCESS} Cleared {count} cached CRD schema(s) from {schema_dir}[/bold green]\n")

    else:
        console.print("\n[bold cyan]Yamlr Schema Subsystem[/bold cyan]")
        console.print("Usage:")
        console.print("  yamlr schema ingest <path>   Ingest CRD YAML manifests into local cache")
        console.print("  yamlr schema list            List currently cached custom schemas")
        console.print("  yamlr schema clean           Clear custom schema cache\n")
