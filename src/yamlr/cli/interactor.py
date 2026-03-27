"""
Yamlr CLI Interactor
--------------------
Handles the interactive "Smart Prompt" and workspace context rendering.
"""

from __future__ import annotations
import os
import sys
from typing import Tuple, Any
from rich.panel import Panel

def render_workspace_context(console: Any, manifest_count: int, has_config: bool, target_kb: str):
    """Renders the descriptive workspace context panel."""
    cwd = os.getcwd()
    display_count = f"{manifest_count}+" if manifest_count >= 500 else str(manifest_count)
    config_status = "[green].yamlr.yaml present[/green]" if has_config else "[yellow]No .yamlr.yaml found[/yellow]"
    
    from yamlr.core.entrypoints.base import CORE_VERSION
    console.print(Panel(
        f"📂 Dir:        [cyan]{os.path.basename(cwd)}[/cyan]\n📄 Manifests:  [cyan]{display_count} YAML files detected[/cyan]\n⚙  Config:     {config_status}\n🎯 K8s Target: [cyan]{target_kb}[/cyan]",
        title=f"[bold cyan]🛡 Yamlr v{CORE_VERSION} – Workspace Context[/bold cyan]", border_style="cyan", expand=False
    ))

def run_smart_prompt(console: Any, manifest_count: int, has_config: bool, is_pro: bool) -> Tuple[str, list]:
    """Runs the interactive prompt to guide the user."""
    if manifest_count > 0:
        suggested_cmd, msg = "yamlr scan .", "Workspace ready for analysis."
        prompt_hint = "(Or type 'h' for full help, 'q' to quit)" if has_config else "(Or type 'i' to init config, 'h' for help, 'q' to quit)"
    else:
        suggested_cmd, msg = "yamlr demo", "No Kubernetes manifests found here."
        prompt_hint = "(Or type 'i' to init config, 'h' for help, 'q' to quit)"
    
    console.print(f"\n{msg}\n[bold]Press Enter to run:[/bold] [bold green]{suggested_cmd}[/bold green]\n[dim]{prompt_hint}[/dim]")
    if is_pro and manifest_count > 0:
        console.print("\n[dim]💎 PRO available in this repo – after scan, try: yamlr heal --harden .[/dim]")
        
    try:
        console.print("\n> ", end="")
        choice = input().strip().lower()
    except (KeyboardInterrupt, EOFError):
        sys.exit(0)
        
    if choice == "h":
        return "help", []
    elif choice == "q":
        sys.exit(0)
    elif choice == "i":
        return "init", []
    elif choice == "":
        cmd_parts = suggested_cmd.split(" ")[1:]
        return cmd_parts[0], cmd_parts[1:]
    else:
        sys.exit(0)
