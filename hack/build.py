#!/usr/bin/env python3
"""
🧬 Yamlr Build System (Enterprise Segregation Edition)
--------------------------------------
Zero-config build script for Windows, Linux, and macOS.

Features:
- Standardized Naming: yamlr (OSS) vs yamlr_pro (Enterprise)
- Zero-Leak: Physically strips yamlr.pro from OSS binary
- Cross-platform dependency management and asset bundling
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

# Configuration Constants
DIST_DIR = Path("dist")
BUILD_DIR = Path("build")
SPEC_DIR = Path("build/specs")
VENV_DIR = Path(".venv_build")
ENTRY_POINT = "src/yamlr/cli/main.py"

# Detection: Check if Pro module is physically present in the source tree
# Note: build.py is in hack/, so parent.parent is the project root
ROOT_DIR = Path(__file__).parent.parent.resolve()
PRO_MODULE_EXISTS = (ROOT_DIR / "src" / "yamlr" / "pro").exists()


def print_header():
    print(r"""
    🧬 Yamlr Build System
    --------------------------------------""")


def print_step(msg):
    print(f"👉 {msg}...", end=" ", flush=True)


def print_done():
    print("\033[1;32m[DONE]\033[0m")


def fail(msg):
    print(f"\n\033[1;31m[ERROR] {msg}\033[0m")
    sys.exit(1)


def run_step(cmd, env=None, cwd=None):
    """Runs a command and directly streams output."""
    try:
        subprocess.run(cmd, env=env, cwd=cwd, check=True)
    except subprocess.CalledProcessError:
        fail(f"Command failed: {' '.join(cmd)}")


def main():
    # 1. Argument Parsing
    parser = argparse.ArgumentParser(description="Yamlr Build System")
    parser.add_argument(
        "--pro",
        action="store_true",
        help="Build Enterprise Edition (requires pro source)",
    )
    args = parser.parse_known_args()[0]

    pro_mode = args.pro
    app_name = "yamlr_pro" if pro_mode else "yamlr"

    if pro_mode and not PRO_MODULE_EXISTS:
        fail("Cannot build Pro version: 'src/yamlr/pro' directory not found.")

    # 2. Setup Context
    os.chdir(ROOT_DIR)
    print_header()
    if pro_mode:
        print("    🚀 Mode: ENTERPRISE EDITION (yamlr_pro)\n")
    else:
        print("    🛡 Mode: COMMUNITY EDITION (yamlr)\n")

    # 3. Cleanup
    print_step("Cleaning previous build artifacts")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    # Surgical Cleanup: Only remove the specific binary we are building
    out_bin = DIST_DIR / (app_name + (".exe" if sys.platform == "win32" else ""))
    if out_bin.exists():
        out_bin.unlink()
    for p in glob.glob("*.spec"):
        os.remove(p)
    print_done()

    # 4. Virtual Environment
    print_step(f"Setting up build environment in {VENV_DIR}")
    if not VENV_DIR.exists():
        venv.create(VENV_DIR, with_pip=True)
    print_done()

    if sys.platform == "win32":
        python_exe = VENV_DIR / "Scripts" / "python.exe"
        pyinstaller_exe = VENV_DIR / "Scripts" / "pyinstaller.exe"
        bin_ext = ".exe"
        path_sep = ";"
    else:
        python_exe = VENV_DIR / "bin" / "python"
        pyinstaller_exe = VENV_DIR / "bin" / "pyinstaller"
        bin_ext = ""
        path_sep = ":"

    # 5. Install Dependencies
    print_step("Installing dependencies (pip)")
    run_step(
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
            "pyinstaller",
        ]
    )
    run_step([str(python_exe), "-m", "pip", "install", "."])
    print_done()

    # 6. Build Binary
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    print_step(f"Compiling {app_name}{bin_ext}")

    cmd = [
        str(pyinstaller_exe),
        "--log-level",
        "ERROR",
        "--noconfirm",
        "--onefile",
        "--clean",
        "--name",
        app_name,
        "--strip",
        "--workpath",
        str(BUILD_DIR),
        "--distpath",
        str(DIST_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--paths",
        str(ROOT_DIR / "src"),
        "--hidden-import",
        "yamlr.core.io",
        "--hidden-import",
        "yamlr.core.pipeline",
        "--hidden-import",
        "ruamel.yaml",
        "--hidden-import",
        "yaml",
        "--hidden-import",
        "requests",
        "--hidden-import",
        "jsonschema",
        "--collect-all",
        "rich",
    ]

    if not pro_mode:
        # 🔒 ZERO-LEAK: Physically strip Pro codebase from OSS binary
        cmd.extend(["--exclude-module", "yamlr.pro"])

    # Add Catalog Assets
    catalog_path = ROOT_DIR / "catalog"
    if catalog_path.exists():
        cmd.extend(["--add-data", f"{catalog_path}{path_sep}yamlr/catalog"])

    # Add rules.yaml (core/data)
    rules_path = ROOT_DIR / "src" / "yamlr" / "core" / "data"
    if rules_path.exists():
        cmd.extend(["--add-data", f"{rules_path}{path_sep}yamlr/core/data"])

    cmd.append(str(ROOT_DIR / ENTRY_POINT))

    run_step(cmd)
    print_done()

    # 7. Verification Summary
    src_bin = DIST_DIR / (app_name + bin_ext)
    if not src_bin.exists():
        fail("Build failed - binary not found!")

    size_mb = src_bin.stat().st_size / (1024 * 1024)
    print("-" * 38)
    print("\033[1;32m✅ Build Complete!\033[0m")
    print(f"📦 Binary: {app_name}{bin_ext}")
    print(f"🚀 Size:   {size_mb:.2f} MB")
    print(f"📍 Location: {src_bin}")
    print("-" * 38)


if __name__ == "__main__":
    main()
