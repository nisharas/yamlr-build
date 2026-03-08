import unittest
import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yamlr.core.engine import YamlrEngine

class TestEngineInit(unittest.TestCase):
    def test_engine_init_with_explicit_catalog(self):
        """Verify engine initializes with an explicit catalog path."""
        workspace = os.getcwd()
        # Use the known root catalog
        catalog = os.path.join(workspace, "catalog", "k8s_v1_distilled.json")
        
        engine = YamlrEngine(workspace_path=workspace, catalog_path=catalog)
        self.assertIsNotNone(engine.catalog)
        self.assertGreater(len(engine.catalog), 0)
        self.assertEqual(engine.workspace, Path(workspace).resolve())

    def test_engine_init_with_default_catalog(self):
        """Verify engine initializes with fallback catalog when None is provided."""
        workspace = os.getcwd()
        engine = YamlrEngine(workspace_path=workspace, catalog_path=None)
        self.assertIsNotNone(engine.catalog)
        self.assertGreater(len(engine.catalog), 0)
        print(f"DEBUG: Default catalog loaded from: {getattr(engine, '_resolved_catalog_for_debug', 'unknown')}")

    def test_engine_quick_factory(self):
        """Verify the static quick() method works as expected."""
        workspace = os.getcwd()
        engine = YamlrEngine.quick(workspace)
        self.assertIsNotNone(engine.catalog)
        self.assertGreater(len(engine.catalog), 0)
        self.assertEqual(engine.workspace, Path(workspace).resolve())

if __name__ == "__main__":
    unittest.main()
