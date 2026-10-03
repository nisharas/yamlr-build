"""Simulates repeated in-memory Python engine calls; it is not a native CLI or filesystem benchmark."""

import os
import time
import psutil
from yamlr.core.engine.base import YamlrEngine
from yamlr.core.engine.safeguard import ResourceGuard

def run_benchmark(count: int = 100000):
    print(f" Starting Python Engine Scale Simulation ({count} calls)...")
    
    # Initialization
    guard = ResourceGuard()
    engine = YamlrEngine.quick(".")
    
    start_time = time.time()
    mem_initial = guard.get_process_memory_mb()
    
    print(f"   Initial Memory: {mem_initial:.2f} MB")
    
    # 🧪 Simulation Loop
    # We simulate the process_file call 100k times with unique paths
    # but same content to measure metadata/reporting overhead.
    mock_content = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: mock-pod\nspec:\n  containers:\n  - name: nginx\n    image: nginx:latest"
    
    for i in range(count):
        if i % 10000 == 0 and i > 0:
            current_mem = guard.get_process_memory_mb()
            print(f"   ✅ Processed {i}... Current Memory: {current_mem:.2f} MB")
            
            if not guard.is_safe_to_proceed():
                print("   ⚠ Scaling Guard Triggered: Throttling Benchmark.")
                time.sleep(0.1)

        # Execute a light-weight pass
        engine.process_file(
            relative_path=f"bench/pod_{i}.yaml",
            content=mock_content,
            full_path=f"/tmp/bench/pod_{i}.yaml",
            config=None,
            start_time=time.time()
        )

    duration = time.time() - start_time
    mem_final = guard.get_process_memory_mb()
    
    print("\n🏁 Benchmark Complete!")
    print(f"   Total Time: {duration:.2f}s")
    print(f"   Throughput: {count / duration:.2f} files/sec")
    print(f"   Final Memory: {mem_final:.2f} MB")
    print(f"   Delta Memory: {mem_final - mem_initial:.2f} MB")
    
    if mem_final < 1024:
        print(f"✅ SIMULATION CHECK: Final process memory remained under 1GB after {count} calls; this is not a certification or peak-memory measurement.")
    else:
        print(f"⚠ SIMULATION WARNING: Final process memory exceeded 1GB after {count} calls; this is not a peak-memory measurement.")

if __name__ == "__main__":
    run_benchmark(100000)
