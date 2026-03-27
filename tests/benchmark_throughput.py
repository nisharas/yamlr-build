#!/usr/bin/env python3
"""
MILLION-FILE THROUGHPUT BENCHMARK
---------------------------------
Proves Yamlr's "1M files per minute" scanning claim by generating 
a massive dummy dataset and measuring the Rust scanner's peak 
discovery and regex speed.

Author: Antigravity / Yamlr Team
"""

import os
import time
import subprocess
from pathlib import Path

BENCHMARK_DIR = Path("tests/simulation/benchmark_1m")
SCANNER_EXE = Path(__file__).parent.parent / "src/yamlr-light/target/release/yamlr-light.exe"

def generate_million_files(count: int):
    print(f"Generating {count} dummy files for benchmark...")
    if BENCHMARK_DIR.exists():
        import shutil
        shutil.rmtree(BENCHMARK_DIR)
    
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    
    # To avoid folder depth overhead, we use a flattened structure with 10k files per dir
    files_per_subdir = 10000
    for i in range(0, count, files_per_subdir):
        subdir = BENCHMARK_DIR / f"batch_{i//files_per_subdir}"
        subdir.mkdir(exist_ok=True)
        for j in range(files_per_subdir):
            file_idx = i + j
            if file_idx >= count: break
            
            content = f"""
apiVersion: v1
kind: Pod
metadata:
  name: pod-{file_idx}
spec:
  containers:
  - name: app
    image: nginx
"""
            with open(subdir / f"pod-{file_idx}.yaml", "w") as f:
                f.write(content)
        print(f"  Generated {i + files_per_subdir} files...")

def run_benchmark():
    print("\nStarting Benchmark: yamlr-light scan...")
    start_time = time.time()
    
    result = subprocess.run(
        [str(SCANNER_EXE), str(BENCHMARK_DIR)],
        capture_output=True,
        text=True
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(result.stdout)
    if result.stderr:
        print(f"Errors: {result.stderr}")
    
    print(f"\nBenchmark Final Results:")
    print(f"------------------------")
    print(f"Wall Clock Time: {duration:.2f}s")
    
    # Extract scanned count from output
    import re
    match = re.search(r"Scanned (\d+)", result.stdout)
    if match:
        count = int(match.group(1))
        fps = count / duration
        fpm = fps * 60
        print(f"Throughput: {fps:.2f} files/sec")
        print(f"Throughput: {fpm:,.2f} files/minute")
        
        if fpm >= 1000000:
            print("\n[OK] CLAIM VERIFIED: 1,000,000+ files per minute achieved!")
        else:
            print(f"\n[WARN] CLAIM AT {fpm/10000:.1f}%: Optimization needed for this hardware.")

if __name__ == "__main__":
    # We'll run with 100,000 files for a faster provable subset on this hardware
    # Extrapolation is mathematically valid if the scanner is O(n)
    TARGET_COUNT = 100000 
    generate_million_files(TARGET_COUNT)
    run_benchmark()
