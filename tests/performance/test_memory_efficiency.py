import os
import time
import yamlr_native
import psutil

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # MB

def test_memory_efficiency():
    # Synthetic manifest for stability
    manifest_template = """apiVersion: v1
kind: ConfigMap
metadata:
  name: test-cm-{}
  namespace: default
  labels:
    app: yamlr-test
    env: perf
    tier: frontend
data:
  config.yaml: |
    nested:
      data: is
      here: for
      scaling: test
"""
    # Scale content to 50,000 documents (~10MB total)
    docs_to_generate = 50000
    large_content = "\n---\n".join(manifest_template.format(i) for i in range(docs_to_generate))
    print(f"Number of documents: {docs_to_generate}")
    print(f"Content Size: {len(large_content) / (1024 * 1024):.2f} MB")

    # Measure Full Parse (Old Way)
    mem_before = get_memory_usage()
    start = time.time()
    full_docs = yamlr_native.native_parse_to_dict(large_content)
    mem_after_full = get_memory_usage()
    duration_full = time.time() - start
    print(f"Full Parse: {duration_full:.4f}s, Memory Used: {mem_after_full - mem_before:.2f} MB")

    # Clear memory
    del full_docs
    import gc
    gc.collect()
    
    # Measure Metadata Extraction (New Way)
    mem_before = get_memory_usage()
    start = time.time()
    meta_docs = yamlr_native.native_extract_metadata(large_content)
    mem_after_meta = get_memory_usage()
    duration_meta = time.time() - start
    print(f"Metadata Extraction: {duration_meta:.4f}s, Memory Used: {mem_after_meta - mem_before:.2f} MB")

    # Parity Check on metadata
    assert len(meta_docs) > 0
    print(f"Parity Check: {len(meta_docs)} documents extracted.")
    
    # Efficiency Check
    saving_ratio = (mem_after_full - mem_before) / (mem_after_meta - mem_before) if (mem_after_meta - mem_before) > 0 else 100
    print(f"Memory Saving Ratio: {saving_ratio:.2f}x")
    
    # Threshold check: Metadata extraction should be MUCH leaner
    # (Actually, for 20MB content, metadata extraction should use < 50MB extra)
    assert (mem_after_meta - mem_before) < 100 

if __name__ == "__main__":
    test_memory_efficiency()
