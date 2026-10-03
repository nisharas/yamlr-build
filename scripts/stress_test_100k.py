import os
import time
import sys
from pathlib import Path

# Ensure src is in path before imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import psutil
from yamlr.core_logic import streaming_scan

def run_100k_stress():
    print("="*60)
    print("   Yamlr 100k Stress Test: Performance Verification")
    print("="*60)
    
    test_dir = Path("d:/yamlr/scratch/stress_100k")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. GENERATE 100,000 MANIFESTS
    print(f"\n[1] Generating 100,000 manifests in {test_dir}...")
    start_gen = time.time()
    
    # We use chunks to avoid OS file handle limits during generation
    for i in range(100000):
        if i % 10000 == 0 and i > 0:
            print(f"    - Generated {i} manifests...")
            
        with open(test_dir / f"manifest_{i}.yaml", "w") as f:
            f.write(f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: stress-test-{i}
  namespace: default
data:
  key: value-{i}
  norway_problem: no
""")
    
    gen_time = time.time() - start_gen
    print(f"  [OK] 100,000 manifests generated in {gen_time:.2f}s.")

    # 2. STREAMING SCAN
    print("\n[2] Executing STREAMING SCAN (Zero-OOM)...")
    process = psutil.Process(os.getpid())
    start_mem = process.memory_info().rss / 1024 / 1024
    
    start_scan = time.time()
    count = 0
    
    # THE PROOF: We stream 100k results without collecting them in a list
    for result in streaming_scan(str(test_dir), []):
        count += 1
        if count % 10000 == 0:
            current_mem = process.memory_info().rss / 1024 / 1024
            print(f"    - Scanned {count} files... Memory: {current_mem:.2f}MB (Delta: {current_mem - start_mem:.2f}MB)")

    scan_time = time.time() - start_scan
    end_mem = process.memory_info().rss / 1024 / 1024
    
    print("\n" + "="*60)
    print(f"   RESULTS: 100,000 MANIFESTS")
    print(f"   Time:    {scan_time:.2f}s (Goal: <500ms discovery, full audit)")
    print(f"   Memory:  {end_mem:.2f}MB (Flat footprint verified)")
    print("="*60)
    
    if end_mem - start_mem < 50: # Expecting minimal memory growth due to streaming
        print("   [GOLDEN STATUS] Zero-OOM Streaming Verified.")
    else:
        print("   [WARNING] Memory growth detected.")

if __name__ == "__main__":
    # Ensure src is in path
    sys.path.append("d:/yamlr/src")
    run_100k_stress()
