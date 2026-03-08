import unittest
import os
import json
from yamlr.core.engine import YamlrEngine
from yamlr.core.pipeline import HealingPipeline

class TestTypoHealing(unittest.TestCase):
    def setUp(self):
        # Force logger to use UTF-8 handler to avoid Windows cp1252 errors
        import logging
        import sys
        
        root = logging.getLogger()
        for h in root.handlers:
            root.removeHandler(h)
            
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(message)s'))
        handler.setLevel(logging.DEBUG)
        
        # This is the key fix for Windows encoding issues
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass # Python < 3.7
            
        root.addHandler(handler)
        root.setLevel(logging.INFO)

        self.workspace = os.getcwd()
        # Use default catalog fallback
        self.engine = YamlrEngine.quick(self.workspace)
        self.pipeline = self.engine.pipeline

    def test_basic_typo_healing(self):
        # Manifest with common typos
        bad_yaml = """
apiVerson: v1
kind: Pod
metdadata:
  name: nginx-typo
spec:
  contianers:
  - name: nginx
    image: nginx
"""
        result = self.pipeline.heal(bad_yaml)
        
        # Verify content has been corrected
        self.assertIn("apiVersion: v1", result.content)
        self.assertIn("metadata:", result.content)
        self.assertIn("containers:", result.content)
        
        # Verify specific audit logs are present
        typo_logs = [log for log in result.logs if "Fixed typo" in log]
        self.assertTrue(len(typo_logs) >= 3, f"Expected at least 3 typo fixes, found: {typo_logs}")
        
        # Check specific log entries
        self.assertTrue(any("apiVerson" in log and "apiVersion" in log for log in result.logs))
        self.assertTrue(any("metdadata" in log and "metadata" in log for log in result.logs))
        self.assertTrue(any("contianers" in log and "containers" in log for log in result.logs))
        

    def test_no_false_positives(self):
        # Manifest with valid keys should not be changed
        clean_yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: clean-pod
spec:
  containers:
  - name: nginx
    image: nginx
"""
        result = self.pipeline.heal(clean_yaml)
        
        # Verify no typo logs
        typo_logs = [log for log in result.logs if "Fixed typo" in log]
        self.assertEqual(len(typo_logs), 0, f"Found unexpected typo fixes: {typo_logs}")

if __name__ == "__main__":
    unittest.main()
