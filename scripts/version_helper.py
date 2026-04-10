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


def write_version(new_version: str) -> bool:
    """Updates the version in pyproject.toml and src/yamlr/version.py.
    
    Why: To ensure packaging and runtime both use the identical version SSOT.
    """
    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"
    version_py = root / "src" / "yamlr" / "version.py"
    
    success = True
    
    # 1. Update pyproject.toml
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8")
        import re
        new_content = re.sub(r'version\s*=\s*"[^"]+"', f'version = "{new_version}"', content)
        pyproject.write_text(new_content, encoding="utf-8")
        print(f"✓ Updated {pyproject.name}")
    else:
        print(f"⚠  Warning: {pyproject} not found.")
        success = False
        
    # 2. Update src/yamlr/version.py
    if version_py.exists():
        content = f'# Yamlr Version Authority\n# -----------------------\n# Single source of truth for the local package version.\n# This file is automatically updated by scripts/version_helper.py.\n\n__version__ = "{new_version}"\n'
        version_py.write_text(content, encoding="utf-8")
        print(f"✓ Updated {version_py.relative_to(root)}")
    else:
        # If it doesn't exist, create it
        version_py.parent.mkdir(parents=True, exist_ok=True)
        content = f'__version__ = "{new_version}"\n'
        version_py.write_text(content, encoding="utf-8")
        print(f"✓ Created {version_py.relative_to(root)}")
        
    return success

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", help="Set the version in pyproject.toml")
    args = parser.parse_args()
    
    if args.set:
        if write_version(args.set):
            print(f"OK: Version updated to {args.set}")
            sys.exit(0)
        else:
            print("ERR: Failed to update version (pyproject.toml not found)")
            sys.exit(1)
            
    print(get_version())
