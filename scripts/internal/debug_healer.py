import logging
from pathlib import Path

from yamlr.cli.utils import resolve_bundled_catalog

from yamlr.core.engine import YamlrEngine

# Configure logging to see Lexer debug output
logging.basicConfig(level=logging.DEBUG, format="%(name)s - %(message)s")


def debug_file(filename):
    path = Path(f"tests/corpus/toxic/{filename}")
    if not path.exists():
        print(f"File not found: {path}")
        return

    print(f"\n--- DEBUGGING {filename} ---")
    content = path.read_text(encoding="utf-8")
    # Use bundled catalog
    catalog_path = resolve_bundled_catalog(None)
    engine = YamlrEngine(workspace_path=".", app_name="Debug", catalog_path=catalog_path)

    result = engine.pipeline.heal(content, file_path=str(path), strict_validation=False, compact=False)

    print(f"Status: {result.status}")
    print("--- HEALED CONTENT START ---")
    print(result.content)
    print("--- HEALED CONTENT END ---")

    if result.status == "SUCCESS":
        import yaml

        try:
            list(yaml.safe_load_all(result.content))
            print("YAML Parsing: SUCCESS")
        except Exception as e:
            print(f"YAML Parsing: FAILED - {e}")


if __name__ == "__main__":
    target_files = ["toxic_000.yaml", "toxic_037.yaml", "toxic_062.yaml", "toxic_026.yaml", "toxic_099.yaml"]
    for filename in target_files:
        debug_file(filename)
