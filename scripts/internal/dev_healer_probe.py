"""Yamlr Development Healer Probe
-------------------------------
Utility for deep-probing corrupt ("toxic") manifest files to verify engine
resilience and parser behavior.
Ensures that the Yamlr engine handles intentionally malformed or hostile
Kubernetes manifests safely without crashes.
"""

import logging
import os
from pathlib import Path

# [Zero-Blindspot] Add src to sys.path for standalone script execution
import sys
sys.path.append(os.path.join(os.getcwd(), "src"))

from yamlr.core.engine import YamlrEngine

# Configure logging to see Lexer debug output
logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")


def debug_file(filename):
    path = Path(f"tests/fixtures/{filename}")
    if not path.exists():
        print(f"File not found: {path}")
        return

    print(f"\n--- DEBUGGING {filename} ---")
    content = path.read_text(encoding="utf-8")

    # [Hardening] Use the engine's 'Magic Moment' factory for self-contained catalog resolution
    engine = YamlrEngine(workspace_path=".", app_name="Debug")

    # Use the process_file entrypoint (v4.2)
    result = engine.process_file(content=content, relative_path=str(path), dry_run=True)

    print(f"Status: {result.status}")
    print("--- HEALED CONTENT START ---")
    print(result.healed_content)
    print("--- HEALED CONTENT END ---")

    if result.status.name == "SUCCESS" or result.status.name == "UNCHANGED":
        import yaml

        try:
            list(yaml.safe_load_all(result.healed_content))
            print("YAML Parsing: SUCCESS")
        except Exception as e:
            print(f"YAML Parsing: FAILED - {e}")


if __name__ == "__main__":
    target_files = ["broken.yaml", "legacy_edge_cases.yaml", "broken_networkpolicy.yaml"]
    for filename in target_files:
        debug_file(filename)
