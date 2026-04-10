import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import os

from yamlr.core.engine.base import YamlrEngine

# Create a fake report for the test
report_path = "tests/fixtures/phase9_opa_report.json"
if not os.path.exists(report_path):
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write('{"result": [{"expressions": [{"value": []}]}]}')

print(f"DEBUG: Starting small test with {report_path}")
engine = YamlrEngine(workspace_path=".", from_report_path=report_path)
print("Engine Initialized")
