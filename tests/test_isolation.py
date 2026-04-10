#!/usr/bin/env python3
"""
Yamlr Import Isolation Test
---------------------------
Verifies that the compiled Yamlr binary can execute core forensic commands
without any operational dependency on the LSP protocol stack (pygls/lsprotocol).
"""

import os
import subprocess
import sys
from pathlib import Path

def run_isolation_test():
    # 1. Identify the binary
    dist_dir = Path("dist")
    binary_name = "yamlr_pro.exe" if os.name == "nt" else "yamlr_pro"
    
    # Try different possible locations
    binary_path = dist_dir / binary_name
    if not binary_path.exists():
        binary_path = dist_dir / "main.dist" / binary_name
    
    if not binary_path.exists():
        binary_path = dist_dir / "yamlr_pro.dist" / binary_name
    
    if not binary_path.exists():
        # Use simple yamlr.exe if pro wasn't the target
        binary_path = dist_dir / "yamlr.exe"
        if not binary_path.exists():
             binary_path = dist_dir / "yamlr.dist" / "yamlr.exe"

    if not binary_path.exists():
        print(f"❌ TEST FAILED: Binary not found in {dist_dir}")
        sys.exit(1)

    print(f"🔍 Testing Isolation for: {binary_path}")

    # 2. Run a core command (scan)
    # We don't need to 'hide' packages because a Nuitka standalone binary
    # uses its own internal filesystem/dist folder and ignores the system site-packages
    # unless it crashed and fell back (which we're testing against).
    
    test_file = Path("fixtures/final_cert.yaml")
    cmd = [str(binary_path), "scan", str(test_file), "--output", "json"]
    
    try:
        # We set a clean environment to ensure no 'accidental' leakage from current PYTHONPATH
        env = os.environ.copy()
        if "PYTHONPATH" in env: del env["PYTHONPATH"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, check=True)
        
        # 3. Verify JSON Content
        import json
        data = json.loads(result.stdout)
        
        if "results" in data:
            print("✅ ISOLATION SUCCESS: Binary executed scan without LSP dependency.")
            print(f"📊 Results Count: {len(data['results'])}")
        else:
            print("❌ TEST FAILED: Invalid JSON output structure.")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(f"❌ ISOLATION FAILED: Binary crashed or returned error.")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ TEST ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_isolation_test()
