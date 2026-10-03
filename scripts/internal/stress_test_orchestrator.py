#!/usr/bin/env python3
"""
YAMLR STRESS TEST ORCHESTRATOR
-------------------------------
Orchestrates 100x scale testing (150k+ manifests) with integrated
peak memory profiling and throughput validation.

Targets:
- Memory: < 1.5 GB
- Throughput: > 50 files/sec
- Stability: Zero Crashes
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

# Budget Constants
DEFAULT_MAX_MEMORY_GB = 1.5
DEFAULT_MIN_FILES_PER_SEC = 50


def get_peak_memory(pid: int) -> float:
    """Returns the peak Resident Set Size (RSS) in GB for a process and its children."""
    try:
        parent = psutil.Process(pid)
        processes = [parent] + parent.children(recursive=True)
        total_rss = sum(p.memory_info().rss for p in processes if p.is_running())
        return total_rss / (1024**3)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0


def run_stress_test(target_dir: Path, timeout: int = 1800):
    """Executes 'yamlr scan' on the target directory and profiles performance."""
    print(f"\n[EXEC] Starting Stress Test on: {target_dir}")

    cmd = [sys.executable, "-m", "yamlr.cli.main", "scan", str(target_dir), "--quiet"]

    start_time = time.perf_counter()
    peak_mem = 0.0

    # Start the process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": "src", "PYTHONUTF8": "1"},
    )

    # Profile while running
    node_count = 0
    edge_count = 0

    try:
        while process.poll() is None:
            current_mem = get_peak_memory(process.pid)
            if current_mem > peak_mem:
                peak_mem = current_mem
            time.sleep(0.5)  # Sample every 500ms
    except Exception as e:
        process.kill()
        print(f"[CRITICAL] Profiling failed: {e}")
        return None

    duration = time.perf_counter() - start_time
    stdout, stderr = process.communicate()

    # Parse graph stats from stderr
    import re

    node_match = re.search(r"built: (\d+) nodes", stderr)
    edge_match = re.search(r"nodes, (\d+) edges", stderr)

    if node_match:
        node_count = int(node_match.group(1))
    if edge_match:
        edge_count = int(edge_match.group(1))

    return {
        "return_code": process.returncode,
        "duration_sec": duration,
        "peak_memory_gb": peak_mem,
        "node_count": node_count,
        "edge_count": edge_count,
        "stdout": stdout,
        "stderr": stderr,
    }


def main():
    parser = argparse.ArgumentParser(description="Yamlr Stress Test Orchestrator")
    parser.add_argument("--count", type=int, default=150000, help="Total manifests to generate/test")
    parser.add_argument("--skip-gen", action="store_true", help="Skip manifest generation")
    parser.add_argument("--output", type=str, default="stress_results.json", help="Results JSON path")
    args = parser.parse_args()

    corpus_dir = Path("tests/simulation/stress_corpus")

    # 1. Generation Phase
    if not args.skip_gen:
        print(f"[STAGE 1/3] Generating {args.count} manifests...")
        gen_start = time.perf_counter()
        # Divide count by 3 since simulate_hyperscale generates 3 clusters
        per_style = args.count // 3
        subprocess.run(
            [sys.executable, "scripts/simulate_hyperscale.py", "--count", str(per_style), "--out", str(corpus_dir)],
            check=True,
        )
        print(f"Done in {time.perf_counter() - gen_start:.2f}s")
    else:
        print("[STAGE 1/3] Skipping generation (using existing corpus)")

    # 2. Execution & Profiling Phase
    print(f"[STAGE 2/3] Executing Stress Test (Target: {args.count} files)...")
    results = run_stress_test(corpus_dir)

    if not results:
        print("[FAIL] Stress test execution failed.")
        sys.exit(1)

    # 3. Validation Phase
    files_per_sec = args.count / results["duration_sec"]
    mem_pass = results["peak_memory_gb"] <= DEFAULT_MAX_MEMORY_GB
    speed_pass = files_per_sec >= DEFAULT_MIN_FILES_PER_SEC
    crash_pass = results["return_code"] == 0

    print("\n" + "=" * 40)
    print(" YAMLR STRESS TEST RESULTS")
    print("=" * 40)
    print(f"Count:      {args.count} manifests")
    print(f"Duration:   {results['duration_sec']:.2f} s")
    print(f"Throughput: {files_per_sec:.2f} files/sec " + ("✅" if speed_pass else "❌"))
    print(f"Peak RAM:   {results['peak_memory_gb']:.3f} GB " + ("✅" if mem_pass else "❌"))
    print(f"Exit Code:  {results['return_code']} " + ("✅" if crash_pass else "❌"))
    print("=" * 40)

    # Export Results
    final_report = {
        "timestamp": datetime.isoformat(datetime.now()),
        "config": {
            "count": args.count,
            "max_memory_gb": DEFAULT_MAX_MEMORY_GB,
            "min_files_per_sec": DEFAULT_MIN_FILES_PER_SEC,
        },
        "results": {
            "duration_sec": results["duration_sec"],
            "peak_memory_gb": results["peak_memory_gb"],
            "files_per_sec": files_per_sec,
            "node_count": results["node_count"],
            "edge_count": results["edge_count"],
            "fidelity": results["edge_count"] / results["node_count"] if results["node_count"] > 0 else 0,
            "success": mem_pass and speed_pass and crash_pass,
        },
    }

    with open(args.output, "w") as f:
        json.dump(final_report, f, indent=2)

    if not final_report["results"]["success"]:
        print("\n[FAIL] Stress test did not meet one or more budget requirements.")
        sys.exit(1)

    print(f"\n[PASS] Stress test completed successfully. Results saved to {args.output}")


if __name__ == "__main__":
    main()
