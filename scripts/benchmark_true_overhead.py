import time
import subprocess
import statistics
import sys
import os

def measure_startup(cmd):
    # Use direct executable to avoid shell overhead
    start = time.perf_counter()
    subprocess.run([sys.executable, "-m", "yamlr.cli.main"] + cmd, capture_output=True)
    return (time.perf_counter() - start) * 1000

if __name__ == "__main__":
    # Ensure src is in path for -m lookup
    sys.path.insert(0, os.path.join(os.getcwd(), "src"))
    os.environ["PYTHONPATH"] = os.path.join(os.getcwd(), "src")
    
    commands = [
        ["--version"],
        ["help"]
    ]
    
    print("--- High Precision Performance Benchmark (No Shell Overhead) ---")
    for cmd in commands:
        # Warmup
        measure_startup(cmd)
        
        latencies = [measure_startup(cmd) for _ in range(5)]
        avg = statistics.mean(latencies)
        print(f"Command: yamlr {' '.join(cmd)}")
        print(f"  Avg Latency: {avg:.2f}ms")
        print(f"  Samples: {[round(l, 2) for l in latencies]}")
    print("----------------------------------------------------------------")
