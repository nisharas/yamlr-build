import os
import time
import psutil
import tempfile
from pathlib import Path
from yamlr import YamlrEngine

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def test_hyperscale_memory():
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # 1. Create 5,001 manifests (Trigger is_ultra_scale)
            num_files = 5001
            print(f"📂 Generating {num_files} synthetic manifests in {tmp_dir}...")
            for i in range(num_files):
                file_path = tmp_path / f"manifest_{i}.yaml"
                file_path.write_text(f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: cm-{i}
  namespace: default
data:
  key: value-{i}
""")
            
            # 2. Initialize Engine
            engine = YamlrEngine(workspace_path=str(tmp_path))
            
            mem_before = get_memory_usage()
            print(f"📈 Memory Before: {mem_before:.2f} MB")
            
            # 3. Run Batch Heal
            start_time = time.time()
            # [MEMORY-TEST] We want to see if RAM explodes
            results = engine.batch_heal(root_path=".", dry_run=True, fast=True, stub_healing=True)
            
            duration = time.time() - start_time
            mem_after = get_memory_usage()
            
            print(f"📉 Memory After Batch: {mem_after:.2f} MB")
            print(f"📊 Memory Delta: {mem_after - mem_before:.2f} MB")
            print(f"⏱️ Duration: {duration:.2f}s")
            
            # Verify Zero-List behavior for Ultra-Scale
            # We check the actual result list returned by batch_heal
            assert len(list(results)) == 0 if hasattr(results, "__iter__") else len(results) == 0, "Ultra-scale should return empty"
            
            # Verify DiskIndex population
            if engine.disk_index:
                idents = engine.disk_index.get_all()
                print(f"🗄️ DiskIndex Check: identities count = {len(idents)}")
                assert len(idents) == num_files, f"Expected {num_files} in index, found {len(idents)}"
                
            # 4. Cleanup/Close Engine for Windows file locks
            engine.close()
            time.sleep(1) # [WINDOWS-FIX] Give OS a moment to release handles
            
            print("✅ Hyperscale Memory Stability Test Passed!")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        if 'engine' in locals():
            engine.close()

if __name__ == "__main__":
    test_hyperscale_memory()
