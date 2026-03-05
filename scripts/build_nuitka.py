#!/usr/bin/env python3
"""
Yamlr Nuitka Build Orchestrator (Google-Quality Edition)
-------------------------------------------------------
Compiles yamlr into high-performance, obfuscated native C binaries.
Maintains strict segregation between Community and Enterprise builds.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
SRC_DIR = ROOT_DIR / "src"
DIST_DIR = ROOT_DIR / "dist"
ENTRY_POINT = SRC_DIR / "yamlr" / "cli" / "main.py"

def build():
    parser = argparse.ArgumentParser(description="Yamlr Nuitka Builder")
    parser.add_argument("--pro", action="store_true", help="Build Enterprise Edition")
    args = parser.parse_args()

    app_name = "yamlr_pro" if args.pro else "yamlr"
    binary_name = f"{app_name}.exe" if sys.platform == "win32" else app_name

    print(f"🚀 Starting Native {app_name.upper()} Build...")

    # Nuitka Base Command
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--follow-imports",
        "--plugin-enable=pylint-warnings",
        f"--output-filename={app_name}",
        "--output-dir=dist",
        "--remove-output",  # Clean build
        "--onefile-tempdir-spec=.yamlr_runtime", # Extract into the excluded folder
        "--include-package=yamlr", # Explicitly include the main package
    ]

    # 🛡 Zero-Leak Logic: Control what modules get compiled
    if not args.pro:
        # Community build: Explicitly block enterprise module
        cmd.append("--nofollow-import-to=yamlr.pro")
        print("    🛡 Security: yamlr.pro excluded from build.")
    else:
        # Enterprise build: Ensure pro module is included
        cmd.append("--follow-import-to=yamlr.pro")
        print("    🚀 Mode: ENTERPRISE (yamlr.pro included)")

    # 📦 Asset Bundling (Catalogs & Rules)
    catalog_path = ROOT_DIR / "catalog"
    if catalog_path.exists():
        cmd.append(f"--include-data-dir={catalog_path}=yamlr/catalog")
    
    # Rules: Direct mapping for reliable resolution in frozen context
    rules_src = SRC_DIR / "yamlr" / "core" / "data" / "rules.yaml"
    if rules_src.exists():
        cmd.append(f"--include-data-file={rules_src}=yamlr/core/entrypoints/rules.yaml")
    
    # Other package data
    cmd.append("--include-package-data=yamlr.core.data")

    # Platform Optimization
    if sys.platform != "win32":
        cmd.append("--lto=yes") # Link Time Optimization (Linux/macOS)

    cmd.append(str(ENTRY_POINT))

    os.chdir(ROOT_DIR)
    
    # Environment Setup
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)
    
    print(f"🛠️ Executing: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True, env=env)
        print(f"\n✅ Compilation successful! Native binary: {DIST_DIR}/{binary_name}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Compilation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
