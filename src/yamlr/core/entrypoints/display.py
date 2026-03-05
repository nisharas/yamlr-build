import platform
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.console import Group
from yamlr.core.bridge import YamlrBridge
from yamlr.core.context import HealContext
from .base import get_console, CORE_VERSION, CATALOG_VERSION

def print_custom_header(invoked_as: str, is_pro: bool, center: bool = False):
    """
    Displays the top-level application banner.
    """
    console = get_console()
    console.print("")
    # Decoupled Branding:
    # OSS Project = Yamlr
    # Commercial Product = Yamlr Enterprise

    if invoked_as == "Yamlr":
        # If running as the main binary, we present the Platform identity if Pro matches
        if is_pro:
            title = "💎 Yamlr Enterprise"
            subtitle = "Powered by Yamlr Engine"
            border = "magenta"
        else:
            title = "🛡 Yamlr"
            subtitle = "Fixes What Others Miss, Safely"
            border = "cyan"
    else:
        # Legacy fallback or alias
        title = "🛡 Yamlr"
        subtitle = "Fixes What Others Miss, Safely"
        border = "cyan"

    from rich import box
    from rich.text import Text
    from rich.align import Align

    # Create Text objects to get proper cell width
    title_text = Text(title)
    subtitle_text = Text(subtitle)

    # Get visual cell widths
    title_width = title_text.cell_len
    subtitle_width = subtitle_text.cell_len

    # Calculate padding needed to center title over the longer subtitle
    if subtitle_width > title_width:
        total_padding = subtitle_width - title_width
        pad_left = total_padding // 2
        pad_right = total_padding - pad_left

        # Add spaces to center the title and force exact width match
        title_centered = (" " * pad_left) + title + (" " * pad_right)
    else:
        title_centered = title

    banner_content = (
        f"[bold]{title_centered}[/bold]\n[dim italic]{subtitle}[/dim italic]"
    )

    header_panel = Panel(
        banner_content,
        border_style=border,
        box=box.ROUNDED,
        padding=(0, 2),
        expand=False,
    )

    if center:
        console.print(Align.center(header_panel))
    else:
        console.print(header_panel)


def print_version(invoked_as: str, is_pro: bool, cluster_version: str = None):
    """
    Displays system information panel.
    """
    console = get_console()
    if is_pro:
        tier = "Enterprise"
        identity = "Yamlr Enterprise"
        border_color = "magenta"
    else:
        tier = "Free Version"
        identity = "Yamlr"
        border_color = "cyan"

    sys_platform = f"{platform.system()} {platform.release()}"
    sys_arch = platform.machine()
    runtime_env = f"Python {platform.python_version()}"

    if not cluster_version:
        cluster_version = HealContext._get_default_cluster_version()

    info_table = Table(box=None, show_header=False, padding=(0, 1))
    info_table.add_column(width=18, justify="left")
    info_table.add_column(justify="left")

    info_table.add_row("Client Version:", f"[bold white]{CORE_VERSION}[/bold white]")
    info_table.add_row(
        "Identity:",
        f"[bold {border_color}]{invoked_as.upper()}[/bold {border_color}] ({tier})",
    )

    if is_pro:
        badge, license_msg, color = YamlrBridge.get_pro_status_display()
        info_table.add_row("License Status:", f"[{color}]{badge}[/{color}]")
        info_table.add_row("", f"[dim]{license_msg}[/dim]")

        try:
            from yamlr.pro import license as pro_license

            trial_status = pro_license.get_trial_status_display()
            if "Trial" in trial_status:
                console.print("\n[bold]Trial Usage:[/bold]")
                console.print(trial_status)
        except Exception:
            pass
    else:
        info_table.add_row("License Status:", "[dim]Community/Unlicensed[/dim]")

    info_table.add_row("Catalog Schema:", f"[yellow]{CATALOG_VERSION}[/yellow]")
    info_table.add_row("Target K8s:", f"[green]{cluster_version}[/green]")
    info_table.add_row("Platform:", f"{sys_platform} ({sys_arch})")
    info_table.add_row("Runtime:", f"{runtime_env}")

    tip_table = Table(box=None, show_header=False, padding=(1, 1, 0, 1))
    tip_table.add_column()

    if not is_pro:
        tip_text = (
            "[bold]💡 Yamlr Enterprise supports auto-detection from kubectl[/bold]"
        )
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
