#!/usr/bin/env python3
"""
Yamlr UNIVERSAL BASELINE CAPTURE
--------------------------------
Goal: Establish absolute semantic parity baseline for cross-platform builds.

Why: To enable bit-for-bit regression testing on Linux, MacOS, and Windows
     without requiring PowerShell (pwsh) dependencies in CI/CD.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
SCRIPTS_DIR = Path(__file__).parent.resolve()
ROOT_DIR = SCRIPTS_DIR.parent
BASELINE_DIR = ROOT_DIR / ".yamlr-baseline"
OUTPUT_DIR = BASELINE_DIR / "outputs"
TESTS_DIR = ROOT_DIR / "tests"

# Constants
YAML_PATTERN = "*.yaml"

def capture():
    print("🛡️ Establishing Universal Golden Shield Baseline...")
    
    # 1. Initialize
    if BASELINE_DIR.exists():
        shutil.rmtree(BASELINE_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Environment Setup
    env = os.environ.copy()
    env["YAMLR_INTERNAL_TEST_MODE"] = "true"
    env["PYTHONPATH"] = str(ROOT_DIR / "src")
    
    # 2. Gather Targets
    targets = []
    # Root tests
    targets.extend(list(TESTS_DIR.glob(YAML_PATTERN)))
    # Fixtures
    targets.extend(list((TESTS_DIR / "fixtures").rglob(YAML_PATTERN)))
    # Performance sample
    perf_dir = TESTS_DIR / "simulation" / "benchmark_1m" / "batch_0"
    if perf_dir.exists():
        targets.extend(list(perf_dir.glob(YAML_PATTERN))[:50])
        
    print(f"🔍 Selected {len(targets)} representative baseline manifests.")
    
    # 3. Capture SARIF artifacts
    for t in targets:
        rel_path = t.relative_to(TESTS_DIR)
        safe_name = str(rel_path).replace(os.sep, "_").replace(".yaml", "")
        out_path = OUTPUT_DIR / f"{safe_name}.sarif"
        
        print(f"🚀 Baseline Capturing: {rel_path}")
        
        cmd = [
            sys.executable, "-m", "yamlr.cli", "main", "scan",
            str(t), "--output", "sarif", "--all", "--harden",
            "--enforce-limits", "--enforce-namespace"
        ]
        
        with open(out_path, "w") as f:
            subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.STDOUT)
            
    print("\n✅ Universal Golden Shield Baseline Established!")
    print(f"📦 Location: {BASELINE_DIR}")

if __name__ == "__main__":
    capture()

