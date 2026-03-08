import os
import sys
from pathlib import Path
from yamlr.core.engine import YamlrEngine

def test_engine_init_with_explicit_catalog():
    """Verify engine initializes with an explicit catalog path."""
    workspace = os.getcwd()
    catalog = os.path.join(workspace, "catalog", "k8s_v1_distilled.json")
    
    engine = YamlrEngine(workspace_path=workspace, catalog_path=catalog)
    assert engine.catalog is not None
    assert len(engine.catalog) > 0
    assert engine.workspace == Path(workspace).resolve()
    print("DEBUG: Explicit catalog init verified.")

def test_engine_init_with_default_catalog():
    """Verify engine initializes with fallback catalog when None is provided."""
    workspace = os.getcwd()
    engine = YamlrEngine(workspace_path=workspace, catalog_path=None)
    assert engine.catalog is not None
    assert len(engine.catalog) > 0
    print(f"DEBUG: Default catalog loaded successfully.")

def test_engine_quick_factory():
    """Verify the static quick() method works as expected."""
    workspace = os.getcwd()
    engine = YamlrEngine.quick(workspace)
    assert engine.catalog is not None
    assert len(engine.catalog) > 0
    assert engine.workspace == Path(workspace).resolve()
    print(f"DEBUG: YamlrEngine.quick() verified.")

if __name__ == "__main__":
    try:
        test_engine_init_with_explicit_catalog()
        test_engine_init_with_default_catalog()
        test_engine_quick_factory()
        print("\n🚀 ENGINE INIT VERIFIED SUCCESSFULLY")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ENGINE INIT FAILED: {e}")
        sys.exit(1)
