import yamlr_native
import time
import os

files_to_test = [
    r"d:\yamlr\tests\fixtures\healthy_manifest.yaml",
    r"d:\yamlr\tests\fixtures\mid_style.yaml"
]

for file_path in files_to_test:
    if not os.path.exists(file_path):
        print(f"Skipping {file_path} - Not found")
        continue

    with open(file_path, "r") as f:
        content = f.read()

    print(f"Testing {os.path.basename(file_path)} ({os.path.getsize(file_path) / 1024:.2f} KB)")
    print("-" * 10)
    
    # Audit
    start = time.time()
    try:
        audit_res = yamlr_native.native_fast_audit(content)
        print(f"Audit: {len(audit_res.get('findings', []))} findings, {audit_res.get('doc_count')} docs")
    except Exception as e:
        print(f"Audit Failed: {e}")
    print(f"Audit took {time.time() - start:.4f}s")
    
    # Parse
    start = time.time()
    try:
        docs = yamlr_native.native_parse_to_dict(content)
        print(f"Parse: {len(docs)} documents")
    except Exception as e:
        print(f"Parse Failed: {e}")
    print(f"Parse took {time.time() - start:.4f}s")
    print("=" * 20)
