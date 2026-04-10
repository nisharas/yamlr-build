import os
import subprocess
import sys
import time

# [VAL-02-3] Performance Benchmarking Suite: Startup p95
# Target: 200ms


def benchmark_startup(runs=10):
    cmd = [sys.executable, "-m", "yamlr.cli.main", "stats"]
    latencies = []

    print(f"🚀 Benchmarking Yamlr CLI startup ({runs} runs)...")

    for _ in range(runs):
        start = time.perf_counter()
        subprocess.run(cmd, capture_output=True, env=os.environ)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    avg = sum(latencies) / runs

    print("\nResults (ms):")
    print(f"  Avg: {avg:.2f}")
    print(f"  p50: {p50:.2f}")
    print(f"  p95: {p95:.2f}")

    if p95 < 200:
        print("\n✅ Performance Goal MET (< 200ms p95)")
    else:
        print(f"\n❌ Performance Goal FAILED (p95 is {p95:.2f}ms, target < 200ms)")


if __name__ == "__main__":
    benchmark_startup()
