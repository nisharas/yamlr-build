"""
CATALOG COMMAND (Hidden)
"""

from __future__ import annotations
import logging
from yamlr.core.catalog_manager import CatalogManager
from yamlr.core.entrypoints.base import get_console

logger = logging.getLogger("yamlr.cli.catalog")
__all__ = ['handle_catalog_command']



def handle_catalog_command(args, target_cluster_version):
    """
    Handles 'catalog' subcommand execution.
    """
    console = get_console()
    catalog_mgr = CatalogManager()
    action = getattr(args, "action", "status")

    if action == "list":
        return _handle_list(console, catalog_mgr)
    elif action == "update":
        return _handle_update(console, catalog_mgr, target_cluster_version)
    elif action == "sync":
        return _handle_sync(console, catalog_mgr)
    elif action == "status":
        return _handle_status(console, catalog_mgr, target_cluster_version)

    return 0


def _handle_list(console, catalog_mgr):
    versions = catalog_mgr.list_installed_versions()
    if versions:
        console.print("[bold]Installed Catalogs:[/bold]")
        for v in versions:
            console.print(f"  • {v}")
    else:
        console.print("[yellow]No local catalogs installed. Using bundled defaults.[/yellow]")
    return 0


def _handle_update(console, catalog_mgr, target_v):
    v = target_v or "v1.31"
    console.print(f"Fetching catalog for [cyan]{v}[/cyan]...")
    if catalog_mgr.fetch_catalog(v):
        console.print(f"[bold green]Successfully updated catalog for {v}[/bold green]")
        return 0
    console.print(f"[bold red]Failed to update catalog for {v}[/bold red]")
    return 1


def _handle_sync(console, catalog_mgr):
    synced = catalog_mgr.sync_all(console)
    if synced:
        console.print(f"\n[bold green]✔ Matrix Sync Complete.[/bold green] Total acquired: {len(synced)}")
    else:
        console.print("\n[dim]No new catalogs acquired (Cache is up to date).[/dim]")
    return 0


def _handle_status(console, catalog_mgr, target_v):
    from yamlr.core.engine.version_utils import get_default_cluster_version
    v = target_v or get_default_cluster_version() or "v1.31"
    resolved = catalog_mgr.resolve_catalog(v)
    source = "Local Cache" if ".yamlr" in resolved.lower() else "Bundled/Fallback"
    
    console.print(f"Target Version: [green]{v}[/green]")
    console.print(f"Resolved Path:  [dim]{resolved}[/dim]")
    console.print(f"Source:         [bold cyan]{source}[/bold cyan]")
    return 0
