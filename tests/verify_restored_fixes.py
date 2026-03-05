import os
import sys
import unittest
import tempfile
import json
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.pipeline import HealingPipeline

class TestRestoredFixes(unittest.TestCase):
    def setUp(self):
        catalog_path = os.path.join(os.path.dirname(__file__), "../catalog/k8s_v1_distilled.json")
        with open(catalog_path, 'r', encoding='utf-8') as f:
            self.catalog = json.load(f)
        self.pipeline = HealingPipeline(self.catalog)

    def test_floating_list_property_recovery(self):
        """
        Tests that flush-left properties under an array key are recovered as list items.
        """
        malformed_yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: malformed-pod
spec:
  containers:
  name: nginx
    image: nginx:1.21
"""
        # Lexer should catch 'containers:' followed by flush-left 'name:'
        res = self.pipeline.heal(malformed_yaml)
        content = res.content
        
        # Should see '- name: nginx' and consistent indentation for image
        self.assertIn("- name: nginx", content)
        self.assertIn("  image: nginx:1.21", content)
        self.assertEqual(res.status.value, "SUCCESS")

    def test_opt_in_network_policy_injection(self):
        """
        Tests that NetworkPolicy is ONLY injected when harden=True.
        """
        namespace_yaml = """
apiVersion: v1
kind: Namespace
metadata:
  name: secure-ns
"""
        # Test Case 1: harden=False (Default)
        res_no_harden = self.pipeline.heal(namespace_yaml, harden=False)
        self.assertNotIn("kind: NetworkPolicy", res_no_harden.content)
        
        # Test Case 2: harden=True
        res_harden = self.pipeline.heal(namespace_yaml, harden=True)
        self.assertIn("kind: NetworkPolicy", res_harden.content)
        self.assertIn("name: default-deny-all", res_harden.content)
        self.assertIn("namespace: secure-ns", res_harden.content)

    def test_multiple_floating_siblings(self):
        """
        Tests the "Multiple flush-left siblings" edge case.
        """
        malformed_yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: multi-sibling
spec:
  containers:
  name: app
  image: app:v1
  name: sidecar
  image: sidecar:v1
"""
        # Refined Lexer should recover these as two separate list items if they all have name:
        # Actually, the user note says: "tracks the 'implicit array context' to consistently heal all related siblings."
        res = self.pipeline.heal(malformed_yaml)
        content = res.content
        
        # Verify both items were recovered
        self.assertIn("- name: app", content)
        self.assertIn("  image: app:v1", content)
        self.assertIn("- name: sidecar", content)
        self.assertIn("  image: sidecar:v1", content)

if __name__ == "__main__":
    unittest.main()
