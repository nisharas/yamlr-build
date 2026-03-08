import os
import sys
import json
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.pipeline import HealingPipeline

def run_repro():
    catalog_path = Path("catalog/k8s_v1_distilled.json")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    pipeline = HealingPipeline(catalog)
    
    repro_file = Path("tests/repro_user_example.yaml")
    content = repro_file.read_text(encoding="utf-8")
    
    print("Testing User Reproduction...")
    result = pipeline.heal(content)
    
    print(f"Status: {result.status.value}")
    print("\nHealed YAML:")
    print(result.content)
    print("\nAudit Log:")
    for log in result.logs:
        print(f"  {log}")

if __name__ == "__main__":
    run_repro()
