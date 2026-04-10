import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path.cwd() / "src"))

from yamlr.core.engine.base import YamlrEngine
from yamlr.models import HealConfig


def test_pipeline_refactor():
    logging.basicConfig(level=logging.INFO)
    engine = YamlrEngine(workspace_path=".")

    # Create a dummy manifest
    test_dir = Path("tests/test_workspace/refactor_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    manifest = test_dir / "pod.yaml"
    manifest.write_text("""
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
  - name: nginx
    image: nginx
""")

    print("Starting batch heal (Pass 1 & 2)...")
    results = engine.batch_heal(str(test_dir), dry_run=True)

    print(f"Processed {len(results)} files.")
    for res in results:
        print(f"File: {res.file_path}, Success: {res.success}, Status: {res.status}")
        if not res.success:
            print(f"Logs: {res.logic_logs}")


if __name__ == "__main__":
    test_pipeline_refactor()
