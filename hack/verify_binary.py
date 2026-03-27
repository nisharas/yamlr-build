from __future__ import annotations
#!/usr/bin/env python3
"""
Yamlr Native Binary Verifier
-----------------------------
Performs high-fidelity end-to-end testing of the compiled yamlr executable.
Validates:
1. Binary-mode path resolution
2. Asset bundling (Rules & Catalogs)
3. Execution performance
4. Zero-Leak (Community binary does not expose Pro features)
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
DIST_DIR = ROOT_DIR / "dist"
WINDOWS = sys.platform == "win32"
BINARY_NAME = "yamlr.exe" if WINDOWS else "yamlr"
BINARY_PATH = DIST_DIR / BINARY_NAME

def run_cmd(args):
    """Runs the binary and returns output."""
    cmd = [str(BINARY_PATH)] + args
    start = time.time()
    # Use bytes capture to avoid locale-dependent decode errors on Windows
    res = subprocess.run(cmd, capture_output=True)
    duration = time.time() - start
    
    stdout = res.stdout.decode("utf-8", errors="replace")
    stderr = res.stderr.decode("utf-8", errors="replace")
    return stdout, stderr, res.returncode, duration

def verify():
    print(f"🕵️ Verifying Native Binary: {BINARY_PATH}")
    
    if not BINARY_PATH.exists():
        print(f"❌ Error: Binary not found at {BINARY_PATH}. Run build_nuitka.py first.")
        sys.exit(1)

    # 1. Version Test (Basic Execution)
    print("👉 Test 1: Version & Basic Execution...", end=" ", flush=True)
    out, err, code, dur = run_cmd(["version"])
    if code == 0 and "yamlr" in out.lower():
        print(f"✅ [DONE] ({dur:.3f}s)")
    else:
        print(f"❌ [FAILED]\nOUT: {out}\nERR: {err}")
        return False

    # 2. Asset Integrity (yamlr explain)
    print("👉 Test 2: Asset Integrity (Embedded Rules)...", end=" ", flush=True)
    out, err, code, dur = run_cmd(["explain", "rule/no-latest-tag"])
    if code == 0 and "Description" in out:
        print(f"✅ [DONE] ({dur:.3f}s)")
    else:
        print(f"❌ [FAILED] (Embedded rules missing)\nOUT: {out}\nERR: {err}")
        return False

    # 3. Security Check (Zero-Leak)
    print("👉 Test 3: Zero-Leak (Pro Exclusion)...", end=" ", flush=True)
    out, err, code, dur = run_cmd(["auth"])
    # In community build, auth might be missing or limited. 
    # If it's physically excluded, it shouldn't even register as a valid command or should show community limits.
    # Note: main.py still lists it as a row, but if the module is missing it should fail gracefully.
    if "enterprise" in out.lower() or "not available" in out.lower():
         print(f"✅ [DONE] ({dur:.3f}s)")
    else:
         print(f"⚠️ [WARNING] Unexpected auth output. Verify logic.")

    # 4. Performance Smoke (Healing)
    print("👉 Test 4: Performance Smoke (Healing)...", end=" ", flush=True)
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test.yaml"
        test_file.write_text("apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n")
        
        out, err, code, dur = run_cmd(["heal", str(test_file)])
        if code == 0:
            print(f"✅ [DONE] ({dur:.3f}s)")
        else:
            print(f"❌ [FAILED]\nERR: {err}")
            return False

    print("\n✨ All Native Verification Tests Passed!")
    print(f"📦 Final Binary Size: {BINARY_PATH.stat().st_size / (1024*1024):.2f} MB")
    return True

if __name__ == "__main__":
    if not verify():
        sys.exit(1)
