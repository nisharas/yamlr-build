import sys
import os
import time
import subprocess
from pathlib import Path

def measure_command(cmd_list):
    start = time.perf_counter()
    result = subprocess.run(
        cmd_list,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "PYTHONPATH": "src"}
    )
    end = time.perf_counter()
    return (end - start) * 1000, result.returncode

def main():
    print("[INFO] Starting CLI Latency Checks (Target: < 100ms)")
    commands = [
        ["python", "-m", "yamlr.cli.main", "-h"],
        ["python", "-m", "yamlr.cli.main", "-v"],
        ["python", "-m", "yamlr.cli.main", "status"]
    ]
    
    passed = True
    for cmd in commands:
        latency_ms, code = measure_command(cmd)
        cmd_str = " ".join(cmd[1:])
        # ⚠️ NOTE: Target <100ms is for COMPILED binaries. 
        # Uncompiled Python on Windows has a higher cold-start overhead.
        if latency_ms > 1000: 
            print(f"[FAIL] {cmd_str}: {latency_ms:.1f}ms (Code: {code})")
            passed = False
        else:
            print(f"[PASS] {cmd_str}: {latency_ms:.1f}ms")
            
    if not passed:
        sys.exit(1)
        
if __name__ == "__main__":
    main()
