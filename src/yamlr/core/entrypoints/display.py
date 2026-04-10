from __future__ import annotations

import platform

# Selective imports for typing only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .base import CATALOG_VERSION, get_console

__all__ = ["print_custom_header", "print_version"]


def print_custom_header(invoked_as: str, is_pro: bool, center: bool = False, title_override: str = None):
    """
    Displays the top-level application banner.
    """
    console = get_console()
    console.print("")
    subtitle = ""
    border = "cyan"

    from yamlr.core.bridge import YamlrBridge

    is_pro = YamlrBridge.is_pro_enabled()

    if is_pro:
        title = "💎 Yamlr Enterprise (Pro)"
        subtitle = "Fixes What Others Miss, Safely"
        border = "magenta"
    else:
        title = "🛡 Yamlr"
        subtitle = "Kubernetes manifest safety engine"
        border = "cyan"

    import os

    from rich.align import Align

    # --- Panel Construction ---
    from rich.panel import Panel
    from rich.table import Table

    from yamlr.core.engine.discovery import fast_manifest_scan

    manifest_count = fast_manifest_scan(os.getcwd())

    config_found = "No .yamlr.yaml found"
    if os.path.exists(".yamlr.yaml") or os.path.exists("yamlr.yaml"):
        config_found = "✓ .yamlr.yaml active"

    from yamlr.core.engine.version_utils import get_default_cluster_version

    cluster_version = get_default_cluster_version(skip_detection=True)

    # Layout for the Panel
    stats_table = Table(box=None, show_header=False, padding=(0, 1))
    stats_table.add_column(width=15, style="cyan")
    stats_table.add_column(style="white")

    stats_table.add_row("📂 Dir:", f"{os.path.basename(os.getcwd())}")
    stats_table.add_row("📄 Manifests:", f"{manifest_count} YAML files detected")
    stats_table.add_row("⚙  Config:", f"{config_found}")
    stats_table.add_row("🎯 K8s Target:", f"{cluster_version}")

    from .base import CORE_VERSION

    header_title = title_override or f"{title} v{CORE_VERSION} – Workspace Context"
    header_panel = Panel.fit(
        stats_table,
        title=f"[bold {border}]{header_title}[/bold {border}]",
        subtitle=f"[dim]{subtitle}[/dim]",
        border_style=border,
        padding=(0, 2),
    )

    if center:
        console.print(Align.center(header_panel))
    else:
        console.print(header_panel)


def print_version(invoked_as: str, is_pro: bool, cluster_version: str = None):
    """
    Displays system information panel.
    """
    from rich.console import Group
    from rich.panel import Panel
    from rich.table import Table

    from yamlr.core.bridge import YamlrBridge

    console = get_console()
    if is_pro:
        tier = "Enterprise (Pro)"
        border_color = "magenta"
    else:
        tier = "Free Version"
        border_color = "cyan"

    sys_platform = f"{platform.system()} {platform.release()}"
    sys_arch = platform.machine()
    runtime_env = f"Python {platform.python_version()}"

    if not cluster_version:
        from yamlr.core.engine.version_utils import get_default_cluster_version

        cluster_version = get_default_cluster_version()

    info_table = Table(box=None, show_header=False, padding=(0, 1))
    # ... lines 102-154
    info_table.add_column(width=18, justify="left")
    info_table.add_column(justify="left")

    from .base import CORE_VERSION

    info_table.add_row("Client Version:", f"[bold white]{CORE_VERSION}[/bold white]")
    info_table.add_row(
        "Identity:",
        f"[bold {border_color}]{invoked_as.upper()}[/bold {border_color}] ({tier})",
    )

    if is_pro:
        badge, license_msg, color = YamlrBridge.get_pro_status_display()
        info_table.add_row("License Status:", f"[{color}]{badge}[/{color}]")
        info_table.add_row("", f"[dim]{license_msg}[/dim]")

        pro_license = YamlrBridge.get_license_module()
        if pro_license and hasattr(pro_license, "get_trial_status_display"):
            trial_status = pro_license.get_trial_status_display()
            if trial_status and "Trial" in trial_status:
                console.print("\n[bold]Trial Usage:[/bold]")
                console.print(trial_status)
    else:
        info_table.add_row("License Status:", "[dim]Community/Unlicensed[/dim]")

    info_table.add_row("Catalog Schema:", f"[yellow]{CATALOG_VERSION}[/yellow]")
    info_table.add_row("Target K8s:", f"[green]{cluster_version}[/green]")
    info_table.add_row("Platform:", f"{sys_platform} ({sys_arch})")
    info_table.add_row("Runtime:", f"{runtime_env}")

    tip_table = Table(box=None, show_header=False, padding=(1, 1, 0, 1))
    tip_table.add_column()

    if not is_pro:
        tip_text = "[bold]💡 Yamlr Enterprise (Pro) supports auto-detection from kubectl[/bold]"
    else:
        tip_text = "[dim]✨ Pro: Auto-detect cluster versions from kubectl/API[/dim]"

    tip_table.add_row(tip_text)

    panel_group = Group(info_table, tip_table)

    console.print(
        Panel.fit(
            panel_group,
            title="[bold]Operational Context[/bold]",
            border_style=border_color,
            padding=(0, 2),
        )
    )

    # [Conversion Hook] Show Pro hint if not pro
    if not is_pro:
        checkout_url = YamlrBridge.get_checkout_url()
        console.print(
            "\n[bold gold1]Unlock high-gravity healing & compliance with Yamlr Enterprise (Pro).[/bold gold1]"
        )
        console.print(f"[dim]Upgrade at: [link={checkout_url}]yamlr.dev/pro[/link][/dim]")
