import sys
from pathlib import Path
import unittest

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from yamlr.core.engine.base import YamlrEngine
from yamlr.core.pipeline.engine import HealingPipeline
from yamlr.core.engine.models import HealStatus

class TestEngineUnification(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("tests/fixtures/unification_test")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.workspace / "service.yaml"
        self.manifest_path.write_text("""
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 9376
""")

    def test_shim_parity(self):
        """Verifies that the HealingPipeline shim correctly redirects to YamlrEngine."""
        try:
            engine = YamlrEngine(workspace_path=str(self.workspace))
            shim = HealingPipeline(catalog=engine.catalog, k8s_version=engine.cluster_version, engine=engine)
            
            content = self.manifest_path.read_text()
            res = shim.process_file(
                engine=engine,
                relative_path="service.yaml",
                content=content,
                full_path=str(self.manifest_path),
                config=None,
                start_time=0.0
            )
            
            self.assertTrue(res.success)
            self.assertEqual(res.file_path, "service.yaml")
            print(f"DEBUG: Status={res.status}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e

    def test_macro_stages_initial(self):
        """Verifies initial ingest and analyze stages in the unified engine."""
        try:
            engine = YamlrEngine(workspace_path=str(self.workspace))
            content = self.manifest_path.read_text()
            
            res = engine.process_file(
                relative_path="service.yaml",
                content=content,
                full_path=str(self.manifest_path),
                config=None,
                start_time=0.0
            )
            
            self.assertGreater(len(res.findings), 0, "Should have found some findings")
            print(f"DEBUG: Findings count = {len(res.findings)}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e

if __name__ == "__main__":
    unittest.main()
