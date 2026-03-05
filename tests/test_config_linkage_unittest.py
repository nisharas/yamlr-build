import unittest
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from yamlr.core.engine import YamlrEngine
from yamlr.core.catalog_manager import CatalogManager

class TestConfigLinkage(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        # Create a catalog minimal file for the engine
        self.catalog_path = self.workspace / "catalog.json"
        self.catalog_path.write_text('{"v1.31": {}}')
        
    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_linkage_harden(self):
        # Create a config file with harden: true
        config_file = self.workspace / ".yamlr.yaml"
        config_file.write_text("healing:\n  harden: true\n")

        engine = YamlrEngine(self.workspace, catalog_path=str(self.catalog_path))
        
        # Manifest to heal
        manifest = self.workspace / "pod.yaml"
        manifest.write_text("""
apiVersion: v1
kind: Pod
metadata:
  name: test
spec:
  containers:
  - name: web
    image: nginx
""")

        # Call heal WITHOUT cli harden flag
        result = engine.audit_and_heal_file("pod.yaml", harden=False, dry_run=True)
        
        # Verify that securityContext was injected (because of config)
        healed = result["healed_content"]
        self.assertIn("securityContext:", healed)
        self.assertIn("runAsNonRoot: true", healed)

    def test_linkage_override(self):
        # Create a config file with harden: false
        config_file = self.workspace / ".yamlr.yaml"
        config_file.write_text("healing:\n  harden: false\n")

        engine = YamlrEngine(self.workspace, catalog_path=str(self.catalog_path))
        
        # Manifest to heal
        manifest = self.workspace / "pod.yaml"
        manifest.write_text("""
apiVersion: v1
kind: Pod
metadata:
  name: test
spec:
  containers:
  - name: web
    image: nginx
""")

        # Call heal WITH cli harden flag
        result = engine.audit_and_heal_file("pod.yaml", harden=True, dry_run=True)
        
        # Verify that securityContext was injected
        healed = result["healed_content"]
        self.assertIn("securityContext:", healed)

if __name__ == "__main__":
    unittest.main()
