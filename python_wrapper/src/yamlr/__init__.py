"""Thin launcher for the yamlr Rust binary via pip/pipx.

Why: Enables `pip install yamlr` with zero Python runtime overhead.
     The actual engine is a pre-compiled, highly-optimized Rust binary
     bundled directly within the wheel (following the 'Ruff' distribution model).
"""

from __future__ import annotations

import importlib.resources
import os
import subprocess
import sys


def _find_binary() -> str:
    """Locate the bundled native yamlr binary across packages and platforms."""
    # 1. Check bundled binary in yamlr.bin package resources
    try:
        pkg = importlib.resources.files("yamlr.bin")
        for name in ("yamlr.exe", "yamlr"):
            candidate = pkg / name
            if candidate.is_file():
                return str(candidate)
    except Exception:
        pass

    # 2. Check relative adjacent bin directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "bin", "yamlr.exe"),
        os.path.join(base_dir, "bin", "yamlr"),
        os.path.join(os.path.dirname(base_dir), "bin", "yamlr.exe"),
        os.path.join(os.path.dirname(base_dir), "bin", "yamlr"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    # 3. Check system PATH
    import shutil
    sys_bin = shutil.which("yamlr")
    if sys_bin:
        return sys_bin

    raise FileNotFoundError(
        "Could not find the bundled yamlr binary. "
        "Please reinstall the package or build from source using cargo build --release."
    )


def main() -> None:
    """Entry point executing the native Rust binary with forwarded CLI arguments."""
    bin_path = _find_binary()
    try:
        proc = subprocess.run([bin_path] + sys.argv[1:])
        sys.exit(proc.returncode)
    except KeyboardInterrupt:
        sys.exit(130)


__all__ = ["_find_binary", "main"]
