from __future__ import annotations

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

from version_helper import get_version  # type: ignore

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
SRC_DIR = ROOT_DIR / "src"
DIST_DIR = ROOT_DIR / "dist"
ENTRY_POINT = SRC_DIR / "yamlr" / "cli" / "main.py"


def _check_baseline():
    """MANDATORY: Gold Standard Baseline Pre-Flight Check"""
    baseline_path = ROOT_DIR / ".yamlr-baseline"
    if not baseline_path.exists():
        print("❌ CRITICAL: Gold Standard Baseline not found.")
        print("   Why: We never build binaries that haven't cleared the semantic parity check.")
        print("   Action: Run 'python scripts/capture_baseline.py' first.")
        sys.exit(1)

def _get_base_cmd(app_name: str) -> list[str]:
    """Generates the base Nuitka command configuration."""
    return [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--low-memory",  # 🛡️ MANDATORY: Prevent MSVC C1002 (Heap Exhaustion)
        "--follow-imports",
        "--jobs=2",      # 🛡️ Safety: Reduce peak memory during heavy module compilation
        "--plugin-enable=pylint-warnings",
        "--plugin-enable=multiprocessing",  # 🛡️ MANDATORY: Fix Windows silent crash
        f"--output-dir={DIST_DIR}",
        f"--output-filename={app_name}",
        "--include-package=yamlr",
        "--include-package=yamlr.healers",
        "--nofollow-import-to=pygls",
        "--nofollow-import-to=lsprotocol",
        "--nofollow-import-to=yamlr.cli.lsp",
        "--nofollow-import-to=yamlr.core.integrations.vscode_lsp",
        "--nofollow-import-to=yamlr.debug",
        "--nofollow-import-to=yamlr.experimental",
        "--include-package=yamlr.core.engine",
        "--include-package=yamlr.core.stages",
        "--include-package=yamlr.core.validation",
        "--include-package=yamlr.core.parser",
        "--include-package=yamlr.core.utils",
        "--include-package=yamlr.parsers",
        "--include-package=yamlr.analyzers",
        "--include-package=yamlr.models",
        "--include-package=yamlr_native",
        "--include-package=ruamel.yaml",
        "--include-package=pydantic",
        "--include-package=pydantic_core._pydantic_core",
        "--include-package=rich",
        "--include-package=jwt",
        "--report=dist/nuitka-build-report.xml",
    ]

def _add_platform_optimizations(cmd: list[str], version: str):
    """Adds OS-specific optimizations and metadata."""
    if sys.platform == "win32":
        cmd.extend([
            f"--windows-file-version={version}",
            f"--windows-product-version={version}",
            "--windows-company-name=Timonel Labs",
            "--windows-product-name=Yamlr Forensic Engine",
        ])
        cmd.append("--lto=no")  # 🛡️ Stability: Disable LTO on Windows to save memory
    else:
        cmd.append("--lto=yes")  # Link Time Optimization (Linux/macOS)

def _add_data_files(cmd: list[str]):
    """Embeds static catalog resources, protocol glue, and deprecations into the build."""
    distilled_src_131 = SRC_DIR / "yamlr" / "catalog" / "k8s_v1.31_distilled.json"
    if distilled_src_131.exists():
        cmd.append(f"--include-data-file={distilled_src_131}=yamlr/catalog/k8s_v1.31_distilled.json")
        cmd.append(f"--include-data-file={distilled_src_131}=yamlr/catalog/k8s_latest_distilled.json")

    catalog_source = ROOT_DIR / "catalog"
    if catalog_source.exists():
        for cat_file in catalog_source.glob("k8s_v*.json"):
            if "1.31" in cat_file.name:
                continue
            cmd.append(f"--include-data-file={cat_file}=yamlr/catalog/{cat_file.name}")

    proxy_src = SRC_DIR / "yamlr" / "cli" / "lsp_proxy.py"
    if proxy_src.exists():
        cmd.append(f"--include-data-file={proxy_src}=lsp_proxy.py")

    rules_src = SRC_DIR / "yamlr" / "core" / "data" / "rules.yaml"
    if rules_src.exists():
        cmd.append(f"--include-data-file={rules_src}=yamlr/core/data/rules.yaml")

    depr_src = SRC_DIR / "yamlr" / "data" / "k8s_deprecations.json"
    if depr_src.exists():
        cmd.append(f"--include-data-file={depr_src}=yamlr/data/k8s_deprecations.json")

    cmd.append("--include-package-data=yamlr.core.data")

def build():
    app_name = "yamlr"
    binary_name = f"{app_name}.exe" if sys.platform == "win32" else app_name
    version = get_version()

    print(f"🚀 Starting Native {app_name.upper()} Build...")

    _check_baseline()

    cmd = _get_base_cmd(app_name)
    _add_platform_optimizations(cmd, version)

    # [Unified Motto] Always include yamlr.pro in the build
    cmd.append("--follow-import-to=yamlr.pro")
    cmd.append("--include-package=yamlr.pro.reconciliation")
    
    # 🛡️ Surface Reduction: Exclude dev/leaks
    cmd.extend([
        "--nofollow-import-to=mypy",
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=setuptools",
        "--nofollow-import-to=pip",
    ])

    _add_data_files(cmd)

    cmd.append(str(ENTRY_POINT))

    os.chdir(ROOT_DIR)
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
