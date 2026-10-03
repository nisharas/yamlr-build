"""Centralized design tokens, icons, and colors for the Yamlr CLI."""

from rich.console import Console
from rich.style import Style

# Design Tokens: Precision-First Palette
COLOR_PRIMARY = "white"
COLOR_SECONDARY = "blue"
COLOR_SUCCESS = "green"
COLOR_WARNING = "yellow"
COLOR_ERROR = "red"
COLOR_ACCENT = "cyan"

import os
import sys

# Icons: Minimalist & Hardened for Windows / Cross-Platform
ICON_SUCCESS = "ok" if os.name == 'nt' else "✔"
ICON_WARNING = "!"
ICON_ERROR   = "x"
ICON_INTEGRITY = "*"
ICON_HEAL    = "[+]"
ICON_SCAN    = "[*]"
ICON_PRO     = "[PRO]"
ICON_ALERT   = "!"

# Style Tokens (Engine Grade)
STYLE_PRIMARY = f"bold {COLOR_PRIMARY}"
STYLE_SECONDARY = f"bold {COLOR_SECONDARY}"
STYLE_SUCCESS = f"bold {COLOR_SUCCESS}"
STYLE_WARNING = f"bold {COLOR_WARNING}"
STYLE_ERROR = f"bold {COLOR_ERROR}"

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False if sys.platform == "win32" else None)


# Descriptions
DESC_SCAN = "Execute an integrity scan of Kubernetes manifests."
DESC_HEAL = "Surgically remediate identified manifest violations."
DESC_PATH = "Target path for discovery (Default: current directory)."
