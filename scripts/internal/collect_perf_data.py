#!/usr/bin/env python3
"""
Performance Data Collector (VAL-02-7)
------------------------------------
Runs Stress Test Orchestrator at multiple scales to generate a
Performance Narrative dataset.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def collect_points():
    # Per-style counts (multiplied by 3 for total)
    counts = [100, 1000, 5000, 10000, 20000]
    history = []

    results_path = Path("stress_results.json")
    history_path = Path("stress_history.json")

    print(f" Starting Performance Data Collection for {len(counts)} points...")

    for c in counts:
        total = c * 3
        print(f"\n[SCALE] Testing {total} manifests (style count: {c})...")

        # Run orchestrator
        # We handle check=False to capture points even if budgets (P1/P2) fail
        try:
            res = subprocess.run(
                [sys.executable, "scripts/stress_test_orchestrator.py", "--count", str(total)],
                check=False,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src", "PYTHONUTF8": "1"},
            )

            if res.returncode != 0:
                print(f"[WARN] Orchestrator exited with code {res.returncode}")

            # Read results
            if results_path.exists():
                with open(results_path, "r") as f:
                    data = json.load(f)
                    point = {
                        "total_files": total,
                        "files_per_sec": data["results"]["files_per_sec"],
                        "peak_mem_gb": data["results"]["peak_memory_gb"],
                        "duration_sec": data["results"]["duration_sec"],
                        "node_count": data["results"].get("node_count", 0),
                        "edge_count": data["results"].get("edge_count", 0),
                        "fidelity": data["results"].get("fidelity", 0.0),
                    }
                    history.append(point)
                    print(f"Captured: {point['files_per_sec']:.2f} files/sec")
            else:
                print(f"[ERROR] stress_results.json not found for count {total}")

        except Exception as e:
            print(f"[ERROR] Benchmark failed for {total} files: {e}")
            break

    # Save History
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    print(f"\n✅ Performance Collection Complete! Data saved to {history_path}")


if __name__ == "__main__":
    collect_points()
