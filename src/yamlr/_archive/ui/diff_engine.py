"""High-fidelity diff computation and terminal rendering engine.

Why: Manifest remediation requires unambiguous visual verification before applying
mutations to disk. Line-level diffs are insufficient for pinpointing single-token
corrections (such as image tags or apiVersion upgrades). This module computes
both structured side-by-side diffs and syntax-highlighted inline word diffs.
"""

import difflib
import re
from typing import List, Optional, Tuple

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from yamlr.ui.theme import console


class SideBySideDiff:
    """Side-by-side diff generator for manifest remediation previews."""
    
    @staticmethod
    def calculate(old_content: str, new_content: str) -> List[Tuple[Optional[str], Optional[str], str]]:
        """Calculates a side-by-side diff between two strings.
        
        Returns:
            List of (left_line, right_line, status)
            Status: "ADDED", "REMOVED", "CHANGED", "UNCHANGED"
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        diff_lines = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for i, j in zip(range(i1, i2), range(j1, j2), strict=False):
                    diff_lines.append((old_lines[i], new_lines[j], "UNCHANGED"))
            elif tag == 'replace':
                max_len = max(i2 - i1, j2 - j1)
                for k in range(max_len):
                    left = old_lines[i1 + k] if i1 + k < i2 else None
                    right = new_lines[j1 + k] if j1 + k < j2 else None
                    diff_lines.append((left, right, "CHANGED"))
            elif tag == 'delete':
                for i in range(i1, i2):
                    diff_lines.append((old_lines[i], None, "REMOVED"))
            elif tag == 'insert':
                for j in range(j1, j2):
                    diff_lines.append((None, new_lines[j], "ADDED"))
                    
        return diff_lines


class InlineWordDiff:
    """Token-level inline word diff engine for Kubernetes manifest repairs.
    
    Computes precise character and word differences across YAML line replacements,
    rendering inline highlights similar to delta and git diff --color-words.
    """

    @staticmethod
    def tokenize_line(line: str) -> List[str]:
        """Tokenizes a line preserving identifiers, punctuation, and whitespace."""
        return re.findall(r"\w+|[^\w\s]+|\s+", line)

    @staticmethod
    def compute_inline_words(old_line: str, new_line: str) -> Tuple[Text, Text]:
        """Highlights word-level additions and deletions using Rich Text objects."""
        old_tokens = InlineWordDiff.tokenize_line(old_line)
        new_tokens = InlineWordDiff.tokenize_line(new_line)

        matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens)
        old_text = Text()
        new_text = Text()

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            old_chunk = "".join(old_tokens[i1:i2])
            new_chunk = "".join(new_tokens[j1:j2])

            if tag == "equal":
                old_text.append(old_chunk, style="dim")
                new_text.append(new_chunk, style="")
            elif tag == "replace":
                old_text.append(old_chunk, style="bold red strike on #3a0000")
                new_text.append(new_chunk, style="bold green underline on #003a00")
            elif tag == "delete":
                old_text.append(old_chunk, style="bold red strike on #3a0000")
            elif tag == "insert":
                new_text.append(new_chunk, style="bold green underline on #003a00")

        return old_text, new_text


def render_inline_diff(old_content: str, new_content: str, title: str = "Manifest Mutation Preview") -> None:
    """Renders a colorized, inline word-level diff into the terminal."""
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Line", style="dim", width=6, justify="right")
    table.add_column("Type", width=4, justify="center")
    table.add_column("Content")

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "replace":
            for _idx, (oi, ni) in enumerate(zip(range(i1, i2), range(j1, j2), strict=False)):
                old_t, new_t = InlineWordDiff.compute_inline_words(old_lines[oi], new_lines[ni])
                table.add_row(str(oi + 1), Text("-", style="bold red"), old_t)
                table.add_row(str(ni + 1), Text("+", style="bold green"), new_t)
            if (i2 - i1) > (j2 - j1):
                for oi in range(i1 + (j2 - j1), i2):
                    table.add_row(str(oi + 1), Text("-", style="bold red"), Text(old_lines[oi], style="bold red"))
            elif (j2 - j1) > (i2 - i1):
                for ni in range(j1 + (i2 - i1), j2):
                    table.add_row(str(ni + 1), Text("+", style="bold green"), Text(new_lines[ni], style="bold green"))
        elif tag == "delete":
            for oi in range(i1, i2):
                table.add_row(str(oi + 1), Text("-", style="bold red"), Text(old_lines[oi], style="bold red"))
        elif tag == "insert":
            for ni in range(j1, j2):
                table.add_row(str(ni + 1), Text("+", style="bold green"), Text(new_lines[ni], style="bold green"))

    console.print(Panel(table, title=f"[bold]{title}[/bold]", subtitle="[dim]Inline Word Diff (delta-mode)[/dim]", border_style="cyan"))


def render_unified_diff(old_content: str, new_content: str, title: str = "Manifest Unified Diff") -> None:
    """Renders a unified diff using inline word highlighting."""
    render_inline_diff(old_content, new_content, title=title)


def render_side_by_side_diff(old_content: str, new_content: str, title: str = "Manifest Side-by-Side Diff") -> None:
    """Renders a two-column side-by-side diff table."""
    diff_rows = SideBySideDiff.calculate(old_content, new_content)
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Original", style="dim", ratio=1)
    table.add_column("Healed (Yamlr)", ratio=1)

    has_diff = False
    for left, right, status in diff_rows:
        if status == "UNCHANGED":
            continue
        has_diff = True
        l_text = Text(left or "", style="bold red" if status in ("REMOVED", "CHANGED") else "dim")
        r_text = Text(right or "", style="bold green" if status in ("ADDED", "CHANGED") else "dim")
        table.add_row(l_text, r_text)

    if has_diff:
        console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style="cyan"))
