import os
import shutil
import sys

# Setup source path
base_dir = os.path.dirname(os.path.abspath(__file__))
# Workspace is d:\yamlr
workspace_path = "d:\\yamlr"
sys.path.append(os.path.join(workspace_path, "src"))

from yamlr.core.engine.base import YamlrEngine
from yamlr.core.engine.processor_helpers import prepare_batch_context


def test_repro():
    engine = YamlrEngine(workspace_path=workspace_path)
    print("Testing batch_heal...")
    try:
        results = engine.batch_heal(
            root_path=workspace_path, extensions=["yaml"], max_depth=10, dry_run=True, task_label="Scanning"
        )
        print("Success! Got {} results".format(len(results)))
    except TypeError as e:
        print(" Caught expected error: {}".format(e))
    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_repro()
