#!/usr/bin/env python3
"""
Yamlr Version Helper
--------------------
Extracts the canonical version from pyproject.toml.
Ensures a single source of truth for all build and packaging steps.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

PYPROJECT_FILE = "pyproject.toml"

# Fix terminal encoding issues (especially on Windows)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, io.UnsupportedOperation):
        pass


def get_version() -> str:
    """Reads project version from root VERSION file or pyproject.toml."""
    root = Path(__file__).resolve().parent.parent
    version_file = root / "VERSION"
    if version_file.exists():
        val = version_file.read_text(encoding="utf-8").strip()
        if val:
            return val

    current = Path(__file__).resolve().parent
    pyproject = None

    for _ in range(5):
        candidate = current / PYPROJECT_FILE
        if candidate.exists():
            pyproject = candidate
            break

        cwd_candidate = Path(os.getcwd()) / PYPROJECT_FILE
        if cwd_candidate.exists():
            pyproject = cwd_candidate
            break

        if current.parent == current:
            break
        current = current.parent

    if not pyproject:
        return "0.1.0"

    try:
        content = pyproject.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.strip().startswith("version = "):
                return line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass

    return "0.1.0"


def write_version(new_version: str) -> bool:
    """Updates the version across all manifests: VERSION, Cargo.toml, pyproject.toml, version.py, vscode, website."""
    import re
    root = Path(__file__).resolve().parent.parent
    success = True

    # 1. Update VERSION file
    version_file = root / "VERSION"
    try:
        version_file.write_text(f"{new_version.strip()}\n", encoding="utf-8")
        print(f"✓ Updated {version_file.name}")
    except Exception as e:
        print(f"⚠ Failed to write {version_file}: {e}")
        success = False

    # 2. Update native_core/Cargo.toml
    cargo_toml = root / "native_core" / "Cargo.toml"
    if cargo_toml.exists():
        content = cargo_toml.read_text(encoding="utf-8")
        new_content = re.sub(r'(\[package\][\s\S]*?version\s*=\s*)"[^"]+"', rf'\g<1>"{new_version}"', content, count=1)
        cargo_toml.write_text(new_content, encoding="utf-8")
        print(f"✓ Updated {cargo_toml.relative_to(root)}")

    # 3. Update pyproject.toml
    pyproject = root / PYPROJECT_FILE
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8")
        new_content = re.sub(r'version\s*=\s*"[^"]+"', f'version = "{new_version}"', content, count=1)
        pyproject.write_text(new_content, encoding="utf-8")
        print(f"✓ Updated {pyproject.name}")

    # 4. Update src/yamlr/version.py
    version_py = root / "src" / "yamlr" / "version.py"
    if version_py.exists():
        content = (
            '"""Single source of truth version definition for yamlr (Python distribution)."""\n\n'
            'import os\n\n'
            '_version_file = os.path.join(os.path.dirname(__file__), "..", "..", "VERSION")\n'
            'if os.path.isfile(_version_file):\n'
            '    with open(_version_file, "r", encoding="utf-8") as _f:\n'
            '        __version__ = _f.read().strip()\n'
            'else:\n'
            f'    __version__ = "{new_version}"\n'
        )
        version_py.write_text(content, encoding="utf-8")
        print(f"✓ Updated {version_py.relative_to(root)}")

    # 5. Update vscode/package.json
    vscode_pkg = root / "vscode" / "package.json"
    if vscode_pkg.exists():
        content = vscode_pkg.read_text(encoding="utf-8")
        new_content = re.sub(r'"version":\s*"[^"]+"', f'"version": "{new_version}"', content, count=1)
        vscode_pkg.write_text(new_content, encoding="utf-8")
        print(f"✓ Updated {vscode_pkg.relative_to(root)}")

    # 6. Update website/package.json
    website_pkg = root / "website" / "package.json"
    if website_pkg.exists():
        content = website_pkg.read_text(encoding="utf-8")
        new_content = re.sub(r'"version":\s*"[^"]+"', f'"version": "{new_version}"', content, count=1)
        website_pkg.write_text(new_content, encoding="utf-8")
        print(f"✓ Updated {website_pkg.relative_to(root)}")

    return success

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Synchronize version across Yamlr codebase.")
    parser.add_argument("--set", help="Set the canonical version across all packages")
    parser.add_argument("--sync", action="store_true", help="Sync canonical version from VERSION to all packages")
    args = parser.parse_args()

    if args.set:
        if write_version(args.set):
            print(f"OK: Version updated to {args.set}")
            sys.exit(0)
        else:
            print("ERR: Failed to update version")
            sys.exit(1)
    elif args.sync:
        ver = get_version()
        if write_version(ver):
            print(f"OK: Synced version {ver} across all packages")
            sys.exit(0)
        else:
            print("ERR: Failed to sync version")
            sys.exit(1)

    print(get_version())
