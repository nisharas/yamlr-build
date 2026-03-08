
"""
Smoke Test for Semantic Healing Flags
"""
import os
import shutil
import tempfile
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.engine import YamlrEngine

def run_test():
    tmp_dir = tempfile.mkdtemp()
    print(f"Working in: {tmp_dir}")
    
    # 1. Create a dummy catalog
    catalog_path = os.path.join(tmp_dir, "catalog.json")
    with open(catalog_path, "w") as f:
        f.write('{"schemas": {}}')
    
    # 2. Create target file
    test_file = os.path.join(tmp_dir, "broken.yaml")
    yaml_content = """
apiVersion: v1
kind: Pod
metadata:
  name: smoke-pod
spec:
  containers:
  - name: nginx
    envFrom:
    - configMapRef:
        name: missing-cm-smoke
"""
    with open(test_file, 'w') as f:
        f.write(yaml_content)
        
    print(f"Created {test_file}")
    
    try:
        # 3. Init Engine
        engine = YamlrEngine(workspace_path=tmp_dir, catalog_path=catalog_path)
        
        # 4. Run Audit
        print("Running Audit...")
        result = engine.audit_and_heal_file(test_file, dry_run=False, identity_mode="infer")
        
        # 5. Run Semantic Fix
        print("Running Semantic Fix...")
        count = engine.apply_semantic_fixes([result], stub_healing=True, allow_unsafe=False, dry_run=False)
        print(f"Modified Count: {count}")
        
        if count == 0:
            print("❌ FAILURE: Zero files modified.")
        else:
            with open(test_file, 'r') as f:
                content = f.read()
            if "missing-cm-smoke" in content and "kind: ConfigMap" in content:
                print("✅ SUCCESS: Found stub content in file!")
                print(content)
            else:
                print("❌ FAILURE: Stub content missing from file!")
                print(content)

    finally:
        # Cleanup
        try:
            shutil.rmtree(tmp_dir)
            print("Cleaned up.")
        except:
            print(f"Warning: Could not clean up {tmp_dir}")

if __name__ == "__main__":
    run_test()
