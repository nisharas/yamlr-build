#!/usr/bin/env python3
"""
Yamlr Version Helper
--------------------
Extracts the canonical version from pyproject.toml.
Ensures a single source of truth for all build and packaging steps.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_version() -> str:
    """Reads project version from pyproject.toml.

    Why: To avoid hardcoding version strings in packaging scripts.
    Returns: Version string (e.g., '1.4.0').
    """
    # Search strategy: Check up the directory tree starting from this file's parent.
    # This ensures we find pyproject.toml even if running from .yamlr_runtime or scripts/
    current = Path(__file__).resolve().parent
    pyproject = None

    # Search up to 5 levels
    for _ in range(5):
        candidate = current / "pyproject.toml"
        if candidate.exists():
            pyproject = candidate
            break

        # Check CWD as well at each step
        cwd_candidate = Path(os.getcwd()) / "pyproject.toml"
        if cwd_candidate.exists():
            pyproject = cwd_candidate
            break

        if current.parent == current:  # Reached root
            break
        current = current.parent

    if not pyproject:
        return "0.0.0-dev"

    try:
        content = pyproject.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.strip().startswith("version = "):
                # Extract "1.4.0" from version = "1.4.0"
                return line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass

    return "0.0.0-unknown"


if __name__ == "__main__":
    print(get_version())
