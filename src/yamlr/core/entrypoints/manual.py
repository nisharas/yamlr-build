"""
MANUAL COMMAND - Local Documentation Viewer
-------------------------------------------
Renders the full USER_GUIDE.md or specific command manuals directly in the terminal.
"""

from __future__ import annotations

import glob
import os

from rich.markdown import Markdown
from rich.table import Table

from yamlr.core.bridge import YamlrBridge
from yamlr.core.entrypoints.base import get_console
from yamlr.core.entrypoints.display import print_custom_header

__all__ = ["handle_manual_command", "print_toc"]


def handle_manual_command(args):
    """
    Displays the User Guide or specific command manuals.
    """
    console = get_console()
    invoked_as = YamlrBridge.get_invoked_command()
    is_pro = YamlrBridge.is_pro_enabled()
    topic = getattr(args, "topic", None)

    # 1. Base Directory Discovery
    # Priority: ENV > Standard Discovery
    from yamlr.core.utils import resolve_bundled_asset

    docs_root = os.getenv("Yamlr_DOCS_PATH")

    if not docs_root or not os.path.exists(docs_root):
        # Use robust discovery for the User Guide and derive the root
        ug_path = resolve_bundled_asset("docs/USER_GUIDE.md")
        if ug_path:
            docs_root = str(ug_path.parent)
        else:
            # Fallback to just searching for the docs dir itself
            docs_dir = resolve_bundled_asset("docs")
            if docs_dir:
                docs_root = str(docs_dir)
            else:
                docs_root = os.path.join(os.getcwd(), "docs")

    cli_docs_dir = os.path.join(docs_root, "cli")
    user_guide_path = os.path.join(docs_root, "USER_GUIDE.md")

    # 2. Topic Handling
    target_file = None
    if topic:
        # Normalize topic name (dashes to underscores) for file matching
        topic = topic.replace("-", "_")

        # Special Case: config -> CONFIGURATION.md
        if topic == "config":
            config_guide = os.path.join(docs_root, "CONFIGURATION.md")
            if os.path.exists(config_guide):
                target_file = config_guide
            else:
                console.print("[red]❌ Could not locate the Yamlr Configuration Guide.[/red]")
                return 1
        else:
            # Try to find yamlr_{topic}.md
            potential_file = os.path.join(cli_docs_dir, f"yamlr_{topic}.md")
            if os.path.exists(potential_file):
                target_file = potential_file
            else:
                console.print(f"[yellow]⚠️  Manual topic '{topic}' not found.[/yellow]\n")
                print_toc(console, cli_docs_dir)
                return 1
    else:
        # Show User Guide by default
        if os.path.exists(user_guide_path):
            target_file = user_guide_path
        else:
            console.print("[red]❌ Could not locate the offline Yamlr User Guide.[/red]")
            print_toc(console, cli_docs_dir)
            return 1

    # 3. Rendering
    print_custom_header(invoked_as, is_pro, center=True)

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
        console.print(Markdown(content))

        # If it was the main user guide, add a nudge to explore topics
        if not topic:
            console.print(
                "[bold cyan]💡 TIP:[/bold cyan] View specific command manuals using: [bold]yamlr manual <command>[/bold]"
            )
            console.print(
                "[dim](e.g., yamlr manual scan, yamlr manual config, yamlr manual rules, yamlr manual heal)[/dim]"
            )
            console.print(
                "[bold cyan]🔎 DISCOVERY:[/bold cyan] For deep dives into specific rules or scaling, run: [bold]yamlr explain config/discovery[/bold]\n"
            )

    except Exception as e:
        console.print(f"[red]❌ Error reading documentation: {e}[/red]")
        return 1

    return 0


def print_toc(console, cli_docs_dir):
    """Prints a table of available manual topics."""
    if not os.path.exists(cli_docs_dir):
        console.print("[dim]No command-specific manuals discovered locally.[/dim]")
        return

    table = Table(title="Available Manual Topics", box=None, show_header=True, header_style="bold magenta")
    table.add_column("Topic", style="cyan")
    table.add_column("Tier", style="dim white")
    table.add_column("Command", style="green")

    # [EPIC-13] Strategic Tiering: Define Pro/Executive commands
    PRO_COMMANDS = {
        "secure",
        "dna",
        "evidence",
        "roi",
        "stats",
        "audit",
        "graph",
        "idp_export",
        "pulse",
        "mcp",
        "rollback",
    }

    # Get all yamlr_*.md files
    files = glob.glob(os.path.join(cli_docs_dir, "yamlr_*.md"))
    topics = []
    for f in sorted(files):
        name = os.path.basename(f).replace("yamlr_", "").replace(".md", "")
        if name not in ["manual"]:  # manual.md is meta
            topics.append(name)

    if "config" not in topics:
        topics.append("config")

    # Tiered Sorting: Free first, then Pro
    sorted_topics = sorted(topics, key=lambda x: (x in PRO_COMMANDS, x))

    # Grid layout for the TOC
    for t in sorted_topics:
        tier = "[PRO]" if t in PRO_COMMANDS else "Free"
        table.add_row(t, tier, f"yamlr manual {t}")

    console.print(table)
    console.print("[dim italic]Run 'yamlr manual <topic>' to view the full specification.[/dim italic]\n")
