import os
import subprocess
import time
import json
import psutil
from pathlib import Path
from typing import Dict, List, Any

# CONFIGURATION
TARGET_WORKSPACE = "tests/stress_test"
MEMORY_THRESHOLD_MB = 2048 # 2GB OOM Safety
PERFORMANCE_REPORT = "tests/PERFORMANCE_DOCKER.md"

class AuditEngine:
    def __init__(self):
        self.results = []
        self._init_report()

    def _init_report(self):
        with open(PERFORMANCE_REPORT, "w") as f:
            f.write("# Yamlr Performance Ledger (v0.1.0)\n\n")
            f.write("| Command | Description | Duration (s) | Max Memory (MB) | Status |\n")
            f.write("|:---|:---|:---|:---|:---|\n")

    def run_command(self, cmd_args: List[str], description: str) -> Dict[str, Any]:
        full_cmd = ["python", "yamlr_entry.py"] + cmd_args
        start_time = time.perf_counter()
        
        # Start Process with NO output capture to avoid buffering issues on large scans
        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        max_rss = 0
        is_oom = False
        
        try:
            p = psutil.Process(proc.pid)
            while proc.poll() is None:
                try:
                    if p.is_running():
                        rss = p.memory_info().rss / (1024 * 1024)
                        if rss > max_rss:
                            max_rss = rss
                        if rss > MEMORY_THRESHOLD_MB:
                            is_oom = True
                            proc.kill()
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
                time.sleep(0.1)
        except (psutil.NoSuchProcess, Exception):
            pass

        proc.wait()
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        result = {
            "command": " ".join(cmd_args),
            "description": description,
            "duration_sec": duration,
            "max_memory_mb": max_rss,
            "exit_code": proc.returncode,
            "is_oom": is_oom,
            "status": "PASS" if proc.returncode == 0 and not is_oom else "FAIL"
        }
        
        with open(PERFORMANCE_REPORT, "a") as f:
            f.write(f"| `{result['command']}` | {result['description']} | {result['duration_sec']:.3f} | {result['max_memory_mb']:.1f} | {result['status']} |\n")
        
        print(f"[{result['status']}] {result['command']:30} | {duration:6.2f}s | {max_rss:6.1f}MB")
        return result

def run_full_audit():
    ae = AuditEngine()
    print("\n   Yamlr Engine Integrity Audit v4.0\n")

    ae.run_command(["--help"], "Basic help discovery")
    ae.run_command(["--help", "--all"], "Full registry discovery")
    ae.run_command(["version"], "Metadata reporting")
    ae.run_command(["doctor"], "System diagnostics")
    ae.run_command(["scan", "tests/fixtures/toxic-collision.yaml"], "Forensic: Identity Collision detection")
    ae.run_command(["scan", "tests/fixtures/deprecated-api.yaml"], "Forensic: Deprecated API detection")
    
    if os.path.exists(TARGET_WORKSPACE):
        ae.run_command(["scan", TARGET_WORKSPACE], "100,000 Manifest Stress Test")

    pro_cmds = ["dna", "roi", "drift", "audit", "graph", "pulse", "fleet", "secure", "rollback", "evidence"]
    for cmd in pro_cmds:
        ae.run_command([cmd], f"Pro Teaser: {cmd}")

    print(f"\n[OK] Audit Complete. Final Report at {PERFORMANCE_REPORT}")

if __name__ == "__main__":
    run_full_audit()
