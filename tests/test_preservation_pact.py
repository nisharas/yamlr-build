import unittest
import os
from pathlib import Path
from yamlr.core.engine import YamlrEngine

class TestPreservationPact(unittest.TestCase):
    """
    Ensures that valid Kubernetes manifests are preserved exactly (zero mutation).
    This is the "Pact" that guarantees Yamlr doesn't break what's already working.
    """
    
    def setUp(self):
        self.workspace = Path("tests/pact_workspace")
        self.workspace.mkdir(exist_ok=True)
        self.engine = YamlrEngine.quick(str(self.workspace))
        
    def test_preservation_of_valid_manifests(self):
        manifests = [
            # 1. Simple Pod
            """apiVersion: v1
kind: Pod
metadata:
  name: valid-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.19
""",
            # 2. Deployment with flow-style
            """apiVersion: apps/v1
kind: Deployment
metadata:
  name: flow-deploy
spec:
  replicas: 3
  selector:
    matchLabels: {app: flow}
  template:
    metadata:
      labels: {app: flow}
    spec:
      containers:
      - name: web
        image: nginx
""",
            # 3. Numeric variations that are valid
            """apiVersion: v1
kind: ConfigMap
metadata:
  name: numeric-cm
data:
  int_val: '123'
  bool_val: 'true'
  hex_val: '0x12'
"""
        ]
        
        for i, content in enumerate(manifests):
            test_file = self.workspace / f"test_{i}.yaml"
            test_file.write_text(content)
            
            # Run heal
            result = self.engine.audit_and_heal_file(str(test_file.relative_to(self.workspace)), dry_run=True)
            
            # ASSERTION: success=True, status=UNCHANGED
            if result["status"] != "UNCHANGED":
                import difflib
                healed = result.get("healed_content") or ""
                diff = difflib.unified_diff(content.splitlines(), healed.splitlines(), lineterm='')
                print(f"\n--- Mutation Diff for Manifest {i} ---")
                print('\n'.join(diff))
                
            self.assertEqual(result["status"], "UNCHANGED", f"Manifest {i} was mutated or flagged as dirty: {result.get('logic_logs')}")
            
    def tearDown(self):
        import shutil
        if self.workspace.exists():
            shutil.rmtree(self.workspace)

if __name__ == "__main__":
    unittest.main()
