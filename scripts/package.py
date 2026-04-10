from __future__ import annotations

#!/usr/bin/env python3
"""
Yamlr Packaging Script
----------------------
Orchestrates the full build and packaging process:
1. Generates Man Pages (docs/scripts/generate_man_pages.py)
2. Builds Binary (scripts/build_nuitka.py)
3. Creates Distribution Archive (ZIP/TAR) with:
   - Binary
   - Man Pages
   - README & LICENSE
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

from version_helper import get_version

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
DIST_DIR = ROOT_DIR / "dist"
SCRIPTS_DIR = ROOT_DIR / "scripts"
DOCS_DIR = ROOT_DIR / "docs"


def run_step(description, command, env=None):
    print(f"\n📦 [STEP] {description}...")
    try:
        subprocess.run(command, check=True, env=env, cwd=ROOT_DIR)
        print("   ✅ Done.")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e}")
        sys.exit(1)


def create_archive(base_name, items, format="zip"):
    archive_path = DIST_DIR / f"{base_name}.{format}"
    print(f"\n📦 [STEP] Creating Archive: {archive_path.name}...")

    if format == "zip":
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item_path, arc_name in items:
                if item_path.is_dir():
                    for root, _, files in os.walk(item_path):
                        for file in files:
                            full_path = Path(root) / file
                            rel_path = full_path.relative_to(item_path)
                            zf.write(full_path, Path(arc_name) / rel_path)
                else:
                    zf.write(item_path, arc_name)
    else:  # tar.gz
        with tarfile.open(archive_path, "w:gz") as tf:
            for item_path, arc_name in items:
                tf.add(item_path, arcname=arc_name)

    print("   ✅ Archive created.")
    return archive_path


def render_template(src: Path, dst: Path, vars: dict):
    """Renders a template file by replacing @KEY@ with value."""
    print(f"📄 [STEP] Rendering Template: {src.name} -> {dst.name}...")
    text = src.read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace(f"@{k}@", str(v))
    dst.write_text(text, encoding="utf-8")
    print("   ✅ Done.")


def main():
    parser = argparse.ArgumentParser(description="Yamlr Packager")
    parser.add_argument("--pro", action="store_true", help="Build Enterprise Edition")
    args = parser.parse_args()

    # 0. Setup
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()

    # 1. Generate Man Pages
    run_step("Generating Man Pages", [sys.executable, str(DOCS_DIR / "scripts" / "generate_man_pages.py")])

    # 2. Build Binary
    build_cmd = [sys.executable, str(SCRIPTS_DIR / "build_nuitka.py")]
    if args.pro:
        build_cmd.append("--pro")

    # Pass environment variables correctly
    env = os.environ.copy()
    run_step("Compiling Native Binary", build_cmd, env=env)

    # 3. Define Archive Contents
    app_name = "yamlr_pro" if args.pro else "yamlr"
    binary_name = f"{app_name}.exe" if sys.platform == "win32" else app_name

    # Determine OS/Arch for naming
    os_name = platform.system().lower()
    machine = platform.machine().lower()
    version = get_version()
    archive_name = f"{app_name}-{version}-{os_name}-{machine}"

    # 3.5 Render Manifest Templates
    template_vars = {"VERSION": version}
    for t_name in ["yamlr.nuspec", "yamlr.rb", "install.ps1", "install.sh"]:
        t_src = SCRIPTS_DIR / f"{t_name}.in"
        if t_src.exists():
            render_template(t_src, DIST_DIR / t_name, template_vars)

    items_to_archive = [
        # (Source Path, Archive Path)
        (DIST_DIR / binary_name, binary_name),
        (DOCS_DIR / "man" / "man1", "man/man1"),
        (ROOT_DIR / "README.md", "README.md"),
    ]

    if (ROOT_DIR / "LICENSE").exists():
        items_to_archive.append((ROOT_DIR / "LICENSE", "LICENSE"))

    # 4. create Archive
    archive_format = "zip" if sys.platform == "win32" else "tar.gz"
    create_archive(archive_name, items_to_archive, format=archive_format)

    print(f"\n✨ Packaging Complete! Artifacts in {DIST_DIR}")


if __name__ == "__main__":
    main()
