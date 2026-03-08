import os
import sys
import json
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.pipeline import HealingPipeline

def audit_failures():
    corpus_dir = Path("tests/corpus/toxic")
    catalog_path = Path("catalog/k8s_v1_distilled.json")
    
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    pipeline = HealingPipeline(catalog)
    
    files = list(corpus_dir.glob("*.yaml"))
    files.sort()
    target_files = files[:100]
    
    failures = []
    
    for f in target_files:
        try:
            content = f.read_text(encoding="utf-8")
            result = pipeline.heal(content)
            
            if result.status.value != "SUCCESS":
                failures.append((f.name, result.status.value, content, result.logs))
        except Exception as e:
            failures.append((f.name, "CRASH", "", [str(e)]))

    print(f"Total Failures: {len(failures)}")
    for name, status, content, logs in failures:
        print(f"\n--- {name} ({status}) ---")
        # Find the line in logs that mentions identity failure
        id_log = next((l for l in logs if "identity" in l.lower() or "missing" in l.lower()), "No log message")
        print(f"Log excerpt: {id_log}")
        print(f"Content excerpt (first 3 lines):\n" + "\n".join(content.split("\n")[:3]))

if __name__ == "__main__":
    audit_failures()
