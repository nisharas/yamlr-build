#!/usr/bin/env python3
"""
Yamlr CI: Version Synchronization Guard
--------------------------------------
Verifies that all packaging and distribution artifacts are in sync
with the canonical version defined in pyproject.toml.

Why: To prevent version drift and ensure $20M+ M&A readiness via
     automated integrity checks.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add scripts dir to path to import version_helper
sys.path.append(str(Path(__file__).parent.parent))
from version_helper import get_version


def verify_sync():
    """Main verification logic."""
    canonical_version = get_version()
    print(f"[CI] Canonical Version (pyproject.toml): {canonical_version}")

    root = Path(__file__).parent.parent.parent.resolve()
    dist_dir = root / "dist"

    # Files to check (if they exist in dist/ after a build)
    to_check = ["yamlr.nuspec", "yamlr.rb", "install.ps1", "install.sh"]

    errors = 0

    # 1. Check if templates still contain @VERSION@ (they should)
    scripts_dir = root / "scripts"
    for t_name in to_check:
        t_src = scripts_dir / f"{t_name}.in"
        if not t_src.exists():
            print(f"[FAIL] Missing template: {t_src.name}")
            errors += 1
            continue

        content = t_src.read_text(encoding="utf-8")
        if "@VERSION@" not in content:
            print(f"[FAIL] Template {t_src.name} is missing @VERSION@ placeholder")
            errors += 1
        else:
            print(f"[PASS] Template {t_src.name} has placeholder.")

    # 2. Check rendered files in dist/ (if present)
    if dist_dir.exists():
        print(f"[CI] Checking rendered files in {dist_dir}...")
        for r_name in to_check:
            r_path = dist_dir / r_name
            if r_path.exists():
                content = r_path.read_text(encoding="utf-8")
                if canonical_version not in content:
                    print(f"[FAIL] Rendered file {r_name} version mismatch.")
                    print(f"    Expected: {canonical_version}")
                    errors += 1
                elif "@VERSION@" in content:
                    print(f"[FAIL] Rendered file {r_name} still contains placeholder!")
                    errors += 1
                else:
                    print(f"[PASS] Rendered file {r_name} is in sync.")
            else:
                print(f"[SKIP] Rendered file {r_name} not found in dist/ (run package.py first).")

    if errors > 0:
        print(f"\n[CI] Version verification failed with {errors} errors.")
        sys.exit(1)

    print("\n[OK] All versions are synchronized.")
    sys.exit(0)


if __name__ == "__main__":
    verify_sync()
