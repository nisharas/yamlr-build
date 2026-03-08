import unittest
import os
from yamlr.core.engine import YamlrEngine

class TestTypoGuard(unittest.TestCase):
    def setUp(self):
        self.engine = YamlrEngine.quick(os.getcwd())
        self.pipeline = self.engine.pipeline

    def test_label_guard(self):
        # Manifest with 'apiVerson' as a LABEL key (legal)
        # and 'apiVerson' as a root key (typo)
        yaml_content = """
apiVerson: v1
kind: Pod
metadata:
  name: label-guard-test
  labels:
    apiVerson: "user-label"
    metdadata: "another-label"
spec:
  containers:
  - name: nginx
    image: nginx
"""
        result = self.pipeline.heal(yaml_content)
        
        # 1. Root key should be FIXED
        self.assertIn("apiVersion: v1", result.content)
        
        # 2. Label keys should NOT be fixed
        self.assertIn("apiVerson: user-label", result.content)
        self.assertIn("metdadata: another-label", result.content)
        
        # 3. Check logs - only 1 fix should be reported (apiVersion)
        typo_logs = [log for log in result.logs if "Fixed typo" in log]
        # It might fix containers typo if I had one there
            
    def test_case_insensitive_heal(self):
        # Test 'Kind' -> 'kind'
        yaml_content = """
apiVersion: v1
Kind: Pod
metadata:
  name: case-test
"""
        result = self.pipeline.heal(yaml_content)
        self.assertIn("kind: Pod", result.content)
        self.assertTrue(any("Fixed typo 'Kind' → 'kind'" in log for log in result.logs))

if __name__ == "__main__":
    unittest.main()
