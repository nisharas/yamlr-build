from __future__ import annotations

from pathlib import Path
from yamlr.core.bridge import ProStatus, YamlrBridge

__all__ = ["handle_auth_command"]


def handle_auth_command(args, console):
    """
    Manages Yamlr Enterprise (Pro) authentication via OIDC or Session Key.
    """
    # [PRO] Lazy import to maintain tier isolation
    try:
        from yamlr.pro.auth import auth_device
    except ImportError:
        console.print("[red]❌ Error: Yamlr Pro extension not found.[/red]")
        return 1

    # 1. Login Mode
    if getattr(args, "auth_action", None) == "login":
        if auth_device.login():
            return 0
        return 1

    # 2. Logout Mode
    if getattr(args, "auth_action", None) == "logout":
        auth_device.logout()
        return 0

    # 3. Status Mode (Default / Status / whoami)
    status, _ = YamlrBridge.check_pro_status()
    console.print("\n[bold cyan]🔐 Yamlr Enterprise (Pro) Status[/bold cyan]")
    console.print("-----------------------------------")

    badge, msg, color = YamlrBridge.get_pro_status_display()
    console.print(f"Status: [{color}]{badge}[/{color}]")
    console.print(f"Detail: {msg}")

    if status == ProStatus.NOT_INSTALLED:
        console.print("\n[dim]To upgrade:[/dim]")
        console.print("  1. Visit [link=https://yamlr.dev/pro]yamlr.dev/pro[/link]")
        console.print("  2. Run [bold green]yamlr auth login[/bold green]")
    elif status.requires_user_action():
        console.print("\n[yellow]Tip: Run 'yamlr auth login' to re-authenticate.[/yellow]")

    return 0
