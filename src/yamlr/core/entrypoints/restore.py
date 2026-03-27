"""
RESTORE COMMAND - Yamlr UX Enhancement
Restores a file from its backup in .yamlr/backups/
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime

from yamlr.core.entrypoints.base import get_console
__all__ = ['handle_restore_command']


def handle_restore_command(args, workspace: str = "."):
    """
    Restores a file from its most recent backup.
    
    Usage: yamlr restore <file>
    """
    console = get_console()
    
    if not args.path or len(args.path) == 0:
        # UX Enhancement: List all available backups if no target specified
        console.print("\n[bold cyan]── yamlr SRE Backup Storage ──[/bold cyan]\n")
        
        workspace_path = Path(workspace).resolve()
        backup_dir = workspace_path / ".yamlr" / "backups"
        
        if not backup_dir.exists():
            console.print("[yellow]No backups found (.yamlr/backups/ does not exist)[/yellow]")
            return 0
        
        backups = list(backup_dir.rglob("*.yaml"))
        if not backups:
            console.print("[yellow]No backup files (.yaml) found in storage.[/yellow]")
            return 0
            
        # Sort by mtime (newest first)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        table = Table(box=None, padding=(0, 2))
        table.add_column("Backup File", style="cyan")
        table.add_column("Original Location", style="dim white")
        table.add_column("Created")
        
        for b in backups[:15]:
            mtime = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            # Infer original location from path structure
            try:
                rel = b.relative_to(backup_dir)
                orig = rel.parent / rel.stem.split('.')[0]
                orig_str = str(orig) + (b.suffix or ".yaml")
            except (ValueError, IndexError, AttributeError):
                orig_str = "Unknown"
                
            table.add_row(b.name, orig_str, mtime)
            
        console.print(table)
        if len(backups) > 15:
            console.print(f"\n[dim]... and {len(backups)-15} older backups.[/dim]")
            
        console.print("\n[dim]Usage: yamlr restore <filename> to recover a specific file.[/dim]\n")
        return 0
    
    target_file = Path(args.path[0])
    workspace_path = Path(workspace).resolve()
    backup_dir = workspace_path / ".yamlr" / "backups"
    
    if not backup_dir.exists():
        console.print("[yellow]No backups found (.yamlr/backups/ does not exist)[/yellow]")
        return 1
    
    # Find backups for this file
    # Backups are stored with structure: backups/<relative-path-dir>/<stem>.<timestamp>.yaml
    try:
        if target_file.is_absolute():
            rel_path = target_file.relative_to(workspace_path)
        else:
            rel_path = target_file
        
        backup_search_dir = backup_dir / rel_path.parent
        stem = target_file.stem
        suffix = target_file.suffix or ".yaml"
        
    except ValueError:
        console.print(f"[red]File is outside workspace: {target_file}[/red]")
        return 1
    
    if not backup_search_dir.exists():
        console.print(f"[yellow]No backups found for {target_file.name}[/yellow]")
        console.print(f"[dim]Searched: {backup_search_dir}[/dim]")
        return 1
    
    # Find all backups matching this file
    backups = list(backup_search_dir.glob(f"{stem}.*{suffix}"))
    
    if not backups:
        console.print(f"[yellow]No backups found for {target_file.name}[/yellow]")
        return 1
    
    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Show available backups
    console.print(f"\n[bold cyan]Available backups for {target_file.name}:[/bold cyan]\n")
    
    for i, backup in enumerate(backups[:10]):
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        time_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
        size_kb = backup.stat().st_size / 1024
        console.print(f"  [{i+1}] {backup.name} ({size_kb:.1f}KB) - {time_str}")
    
    if len(backups) > 10:
        console.print(f"  [dim]... and {len(backups)-10} older backups[/dim]")
    
    # Interactive selection
    console.print()
    choice = console.input("[bold yellow]Restore which backup? (1 for latest, or number): [/bold yellow]")
    
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(backups):
            console.print("[red]Invalid selection[/red]")
            return 1
        selected = backups[idx]
    except ValueError:
        if choice.lower() == 'q' or choice.strip() == '':
            console.print("[dim]Cancelled[/dim]")
            return 0
        console.print("[red]Invalid selection[/red]")
        return 1
    
    # Confirm restoration
    target_path = workspace_path / rel_path
    console.print("\n[bold yellow]About to restore:[/bold yellow]")
    console.print(f"  From: {selected}")
    console.print(f"  To:   {target_path}")
    
    confirm = console.input("\n[bold red]This will overwrite the current file. Continue? (y/N): [/bold red]")
    
    if confirm.lower() != 'y':
        console.print("[dim]Cancelled[/dim]")
        return 0
    
    # Perform restoration
    try:
        import shutil
        shutil.copy2(selected, target_path)
        console.print(f"\n[bold green]✓ Restored {target_file.name} from backup[/bold green]")
        console.print(f"[dim]Backup: {selected.name}[/dim]")
        return 0
    except (shutil.Error, OSError, IOError) as e:
        console.print(f"[red]Restore failed: {e}[/red]")
        return 1
