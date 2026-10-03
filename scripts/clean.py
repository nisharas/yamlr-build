#!/usr/bin/env python3
"""Workspace hygiene and transient artifact purger for Yamlr.

Why: Development, test execution, and CI benchmarks generate ephemeral reports,
     coverage snapshots, compiler intermediates, and synthetic test datasets.
     This script enforces clean repository hygiene without touching any core
     logic, source manifests, or production configurations.
"""
import os
import shutil
from pathlib import Path


def clean():
    """Purges transient artifacts, caches, and build outputs."""
    root = Path(__file__).resolve().parent.parent

    # 1. Ephemeral files in repository root
    root_patterns = [
        "*.log",
        "*.txt",
        "*.sarif",
        "plan_dump.md",
        ".coverage",
        "coverage.json",
        "coverage_report.txt",
        "final_coverage*.txt",
        "telemetry_stats.json",
        "heal_output.txt",
        "evidence-receipt-*.json",
        "all_files_catalog.txt",
        "classified_files.json",
        "yamlr-codebase.md",
    ]

    for pattern in root_patterns:
        for p in root.glob(pattern):
            try:
                print(f"Deleting transient file: {p.name}")
                p.unlink()
            except OSError as e:
                print(f"Error removing {p.name}: {e}")

    # 2. Stray scratch manifests in src/
    src_transients = [
        root / "src" / ".coverage",
        root / "src" / "broken.yaml",
        root / "src" / "sample.yaml",
        root / "src" / ".yamlr.yaml",
    ]
    for p in src_transients:
        if p.exists():
            try:
                print(f"Deleting transient file: src/{p.name}")
                p.unlink()
            except OSError as e:
                print(f"Error removing src/{p.name}: {e}")

    # 3. Ephemeral directories and build caches
    transient_dirs = [
        root / ".pytest_cache",
        root / ".mypy_cache",
        root / ".ruff_cache",
        root / ".hypothesis",
        root / ".shadow-test",
        root / ".yamlr_runtime",
        root / ".yamlr_state",
        root / ".yamlr" / "backups",
        root / "dist",
        root / "build",
        root / "dist_whl",
        root / "scratch",
        root / "vscode" / "audit_vsix",
        root / "native_core" / "target_new",
        root / "website" / ".next",
        root / "website" / "out",
    ]

    for d_path in transient_dirs:
        if d_path.exists():
            print(f"Purging directory: {d_path.relative_to(root)}")
            shutil.rmtree(d_path, ignore_errors=True)

    # 4. Deep pycache purge (excluding virtual environments)
    for p in root.rglob("__pycache__"):
        if ".venv" not in p.parts and "env" not in p.parts:
            print(f"Purging pycache: {p.relative_to(root)}")
            shutil.rmtree(p, ignore_errors=True)

    print("[CLEAN] Workspace sanitized successfully.")


if __name__ == "__main__":
    clean()

