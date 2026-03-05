import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath("src"))

from yamlr.core.engine import YamlrEngine

def test_quick_factory_magic_moment():
    print("Testing Magic Moment: Zero-Config Engine Initialization...")
    
    # Initialize engine with no catalog path
    try:
        engine = YamlrEngine.quick(".")
        print("Engine initialized successfully.")
        print(f"Active K8s Version: {engine.cluster_version}")
        
        # Check if catalog is loaded (either physical or embedded)
        if engine.catalog:
            print("Catalog loaded successfully.")
            if engine.catalog.get("version") == "v1.31.0-embedded":
                print("Using Embedded Magic Fallback!")
            else:
                print("Using Resolved Physical Catalog.")
        else:
            print("Catalog missing!")
            sys.exit(1)

        # Test a simple stream audit
        test_yaml = "kind: Pod\nmetadata:\n  name: test-pod"
        result = engine.audit_stream(test_yaml)
        
        if result.identities:
            print(f"Stream audit completed for: {result.identities[0]['kind']}")
        else:
             print(f"Stream audit completed, but no identities found. Status: {result.status}")
        
    except Exception as e:
        print(f"Magic Moment Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_quick_factory_magic_moment()
