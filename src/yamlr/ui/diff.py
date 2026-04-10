"""
Yamlr DIFF ENGINE
--------------------
Provides rich, colorful diffs for the CLI.
Supports:
- Side-by-side comparison (ideal for batch review)
- Inline diffs (classic git style)
- Syntax highlighting via Rich

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-01-27
"""

from __future__ import annotations

import difflib

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from yamlr.core.entrypoints.base import get_console

console = get_console()

__all__ = ["DiffEngine"]


class DiffEngine:
    """Renders colorful diffs for Kubernetes manifests."""

    @staticmethod
    def render_diff(original: str, healed: str, file_path: str, side_by_side: bool = True):
        """
        Displays a diff between the original and healed content.

        Args:
            original: The raw content before healing.
            healed: The content after healing.
            file_path: Name of the file being modified.
            side_by_side: If True, uses a 2-column layout. False uses unified diff.
        """
        # Handle None cases (means skip, failed read, or pruned in ultra-scale)
        if original is None:
            original = ""
        if healed is None or original == healed:
            console.print(f"[dim]No changes for {file_path}[/dim]")
            return

        # Prepare title
        title = f":wrench: Proposed Changes for [bold cyan]{file_path}[/bold cyan]"

        if side_by_side:
            DiffEngine._render_side_by_side(original, healed, title)
        else:
            DiffEngine._render_inline(original, healed, title)

    @staticmethod
    def _render_side_by_side(original: str, healed: str, title: str):
        """
        Renders two panels side-by-side using smart block extraction.
        Highlights changed lines with background colors.
        """
        matcher = difflib.SequenceMatcher(None, original.splitlines(), healed.splitlines())

        # Prepare table
        table = Table(
            title=title,
            show_header=True,
            header_style="bold magenta",
            expand=True,
            box=None,
        )
        table.add_column("Original (Current)", style="on #3b0e0e", ratio=1)  # Dark red bg for deletions
        table.add_column("Healed (Proposed)", style="on #0e3b0e", ratio=1)  # Dark green bg for additions

        orig_lines = original.splitlines()
        healed_lines = healed.splitlines()

        # If original is effectively empty, show a synthetic hint
        if not original.strip():
            orig_lines = ["(synthetic original – file did not parse; right side shows Yamlr's reconstructed manifest)"]

        # Iterate through matched blocks
        # We want to show EQUAL blocks (context) + REPLACE/DELETE/INSERT blocks

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                DiffEngine._add_equal_region(table, orig_lines, healed_lines, i1, i2, j1, j2)
            elif tag in ["replace", "delete", "insert"]:
                DiffEngine._add_change_region(table, tag, orig_lines, healed_lines, i1, i2, j1, j2)

        console.print(table)
        console.print("[dim italic]Use arrows to scroll if content is long[/dim italic]\n")

    @staticmethod
    def _add_equal_region(table: Table, orig: List[str], healed: List[str], i1: int, i2: int, j1: int, j2: int):
        """Adds an unchanged context block to the diff table, collapsing if too long."""
        block_len = i2 - i1
        if block_len <= 6:
            table.add_row(
                Syntax("\n".join(orig[i1:i2]), "yaml", theme="monokai", start_line=i1 + 1),
                Syntax("\n".join(healed[j1:j2]), "yaml", theme="monokai", start_line=j1 + 1),
            )
        else:
            # Collapse long context
            table.add_row(
                Syntax("\n".join(orig[i1 : i1 + 2]), "yaml", theme="monokai", start_line=i1 + 1),
                Syntax("\n".join(healed[j1 : j1 + 2]), "yaml", theme="monokai", start_line=j1 + 1),
            )
            table.add_row("[dim]... (unchanged) ...[/dim]", "[dim]... (unchanged) ...[/dim]")
            table.add_row(
                Syntax("\n".join(orig[i2 - 2 : i2]), "yaml", theme="monokai", start_line=i2 - 1),
                Syntax("\n".join(healed[j2 - 2 : j2]), "yaml", theme="monokai", start_line=j2 - 1),
            )

    @staticmethod
    def _add_change_region(table: Table, tag: str, orig: List[str], healed: List[str], i1: int, i2: int, j1: int, j2: int):
        """Adds a changed/replaced block to the diff table with background highlighting."""
        left_content = "\n".join(orig[i1:i2]) if tag != "insert" else ""
        right_content = "\n".join(healed[j1:j2]) if tag != "delete" else ""

        table.add_row(
            Syntax(left_content, "yaml", theme="monokai", background_color="#3b0e0e") if left_content else "",
            Syntax(right_content, "yaml", theme="monokai", background_color="#0e3b0e") if right_content else "",
        )

    @staticmethod
    def _render_inline(original: str, healed: str, title: str):
        """Renders a standard unified diff with colors."""
        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                healed.splitlines(keepends=True),
                fromfile="Original",
                tofile="Healed",
                n=3,  # Context lines
            )
        )

        # Build a Rich Text object for the diff
        diff_text = Text()
        for line in diff_lines:
            if line.startswith("---") or line.startswith("+++"):
                diff_text.append(line, style="bold magenta")
            elif line.startswith("@@"):
                diff_text.append(line, style="cyan")
            elif line.startswith("-"):
                diff_text.append(line, style="red")
            elif line.startswith("+"):
                diff_text.append(line, style="green")
            else:
                diff_text.append(line, style="dim white")

        console.print(Panel(diff_text, title=title, expand=False, border_style="blue"))
