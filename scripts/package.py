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
import io
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

# Fix terminal encoding issues (especially on Windows)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, io.UnsupportedOperation):
        pass

# [Infrastructure] Add SCRIPTS_DIR to path for internal helper imports
SCRIPTS_DIR = Path(__file__).parent.resolve()
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

from version_helper import get_version

DONE_MSG = "   ✅ Done."

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
DIST_DIR = ROOT_DIR / "dist"
SCRIPTS_DIR = ROOT_DIR / "scripts"
DOCS_DIR = ROOT_DIR / "docs"


def run_step(description, command, env=None):
    print(f"\n [STEP] {description}...")
    try:
        subprocess.run(command, check=True, env=env, cwd=ROOT_DIR)
        print(DONE_MSG)
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e}")
        sys.exit(1)


def create_archive(base_name, items, format="zip"):
    archive_path = DIST_DIR / f"{base_name}.{format}"
    print(f"\n [STEP] Creating Archive: {archive_path.name}...")

    if format == "zip":
        _create_zip_archive(archive_path, items)
    else:  # tar.gz
        _create_tar_archive(archive_path, items)

    print("   ✅ Archive created.")
    return archive_path


def _create_zip_archive(archive_path, items):
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item_path, arc_name in items:
            if item_path.is_dir():
                _add_dir_to_zip(zf, item_path, arc_name)
            else:
                zf.write(item_path, arc_name)


def _add_dir_to_zip(zf, item_path, arc_name):
    for root, _, files in os.walk(item_path):
        for file in files:
            full_path = Path(root) / file
            rel_path = full_path.relative_to(item_path)
            zf.write(full_path, Path(arc_name) / rel_path)


def _create_tar_archive(archive_path, items):
    with tarfile.open(archive_path, "w:gz") as tf:
        for item_path, arc_name in items:
            tf.add(item_path, arcname=arc_name)


def render_template(src: Path, dst: Path, vars: dict):
    """Renders a template file by replacing @KEY@ with value."""
    print(f"📄 [STEP] Rendering Template: {src.name} -> {dst.name}...")
    text = src.read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace(f"@{k}@", str(v))
    dst.write_text(text, encoding="utf-8")
    print("   ✅ Done.")


def build_native_extension():
    """Compiles the Rust native extension and stages it for bundling."""
    native_dir = ROOT_DIR / "native_core" if (ROOT_DIR / "native_core").exists() else ROOT_DIR / "src" / "yamlr_native"
    if not native_dir.exists():
        print("⚠  Skip: native_core not found. Standard Python-only mode it is.")
        return

    # 1. Build via Maturin
    manifest_arg = ["--manifest-path", str(native_dir / "Cargo.toml")] if (native_dir / "Cargo.toml").exists() else []
    maturin_cmd = [sys.executable, "-m", "maturin", "build", "--release"] + manifest_arg
    run_step("Compiling Rust Surgical Core (Maturin)", maturin_cmd, env=os.environ.copy())

    # 2. Localize the .pyd/.so
    # Maturin puts it in target/release/
    target_dir = native_dir / "target" / "release" if (native_dir / "target" / "release").exists() else ROOT_DIR / "target" / "release"
    
    # On Windows, Maturin builds a .dll. On Linux, a .so.
    # We need to rename it to 'yamlr_native.pyd' or 'yamlr_native.so' for top-level import.
    src_name = "yamlr_native.dll" if sys.platform == "win32" else "libyamlr_native.so"
    dst_name = "yamlr_native.pyd" if sys.platform == "win32" else "yamlr_native.so"
    
    src_ext = target_dir / src_name
    
    # Fallback search if exact name not found
    if not src_ext.exists():
        ext_pattern = "*.dll" if sys.platform == "win32" else "*.so"
        found = list(target_dir.glob(ext_pattern))
        if found:
            src_ext = found[0]

    if not src_ext.exists():
        print(f"❌ FAIL: Could not find compiled native extension: {src_name}")
        sys.exit(1)

    dst_ext = ROOT_DIR / "src" / dst_name
    
    print(f" [STEP] Localizing Native Ext: {src_ext.name} -> src/{dst_name}")
    shutil.copy2(src_ext, dst_ext)
    print("   ✅ Done.")


def main():
    argparse.ArgumentParser(description="Yamlr Packager").parse_args()

    # 0. Setup
    if DIST_DIR.exists():
        print(f"🧹 [STEP] Cleaning {DIST_DIR.name}...")
        # On Windows, rmtree often fails due to locked handles (Nuitka, AV, etc.)
        # We try shutil first, then fallback to aggressive shell command
        try:
            shutil.rmtree(DIST_DIR)
        except Exception:
            if sys.platform == "win32":
                subprocess.run(["cmd", "/c", "rd", "/s", "/q", str(DIST_DIR)], check=False)
            else:
                shutil.rmtree(DIST_DIR, ignore_errors=True)
    
    if not DIST_DIR.exists():
        DIST_DIR.mkdir()

    # 1. Generate Man Pages
    run_step("Generating Man Pages", [sys.executable, str(DOCS_DIR / "scripts" / "generate_man_pages.py")])

    # 2. Build Native Extension (Rust)
    build_native_extension()

    # 3. Build Binary
    build_cmd = [sys.executable, str(SCRIPTS_DIR / "build_nuitka.py")]

    # Pass environment variables correctly
    env = os.environ.copy()
    run_step("Compiling Native Binary", build_cmd, env=env)

    # 3. Define Archive Contents
    app_name = "yamlr"
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

    print(f"\n Packaging Complete! Artifacts in {DIST_DIR}")


if __name__ == "__main__":
    main()
