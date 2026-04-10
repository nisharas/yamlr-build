"""
Yamlr DISCOVERY ENGINE
----------------------
High-performance file system crawlers for manifest discovery.
"""

from __future__ import annotations

import os

__all__ = ["fast_manifest_scan"]


def fast_manifest_scan(root: str, max_count: int = 500) -> int:
    """
    ULTRA-FAST shallow scan for the Magic Moment panel.
    Uses scandir for performance and strictly limits recursion depth.
    """
    count = 0
    ignore_dirs = {".git", ".venv", "node_modules", "__pycache__", "bin", "obj"}
    stack = [(root, 0)]

    while stack and count < max_count:
        curr_dir, depth = stack.pop()
        try:
            with os.scandir(curr_dir) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        if depth < 2 and not entry.name.startswith(".") and entry.name not in ignore_dirs:
                            stack.append((entry.path, depth + 1))
                    elif entry.is_file(follow_symlinks=False) and entry.name.lower().endswith((".yaml", ".yml")):
                        count += 1
                        if count >= max_count:
                            return count
        except OSError:
            continue

    return count
