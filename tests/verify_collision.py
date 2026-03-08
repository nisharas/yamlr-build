import os
import sys
import json
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.pipeline import HealingPipeline

def verify_collision():
    catalog_path = Path("catalog/k8s_v1_distilled.json")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    pipeline = HealingPipeline(catalog)
    
    collision_file = Path("tests/test_identity_collision.yaml")
    content = collision_file.read_text(encoding="utf-8")
    
    print("Testing Identity Collision...")
    result = pipeline.heal(content)
    
    print(f"Status: {result.status.value}")
    print(f"Logs: {result.logs}")
    
    # Check if collision error is in logs
    collision_logged = any("IDENTITY_COLLISION" in l for l in result.logs)
    print(f"Collision Detected in Logs: {collision_logged}")
    
    if not collision_logged:
        # Check scanner logs directly if possible via standard logging audit
        pass

if __name__ == "__main__":
    verify_collision()
