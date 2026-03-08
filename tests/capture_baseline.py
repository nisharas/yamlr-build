import sys
import json
import os
from pathlib import Path
from dataclasses import asdict

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.engine import YamlrEngine

def capture():
    print("📸 Capturing Pre-Refactor Baseline...")
    workspace = Path(__file__).parent.parent
    engine = YamlrEngine.quick(str(workspace))
    
    # We use tests/fixtures and tests/corpus as stable sets
    targets = [workspace / "tests" / "fixtures", workspace / "tests" / "corpus"]
    
    all_results = []
    for target in targets:
        if not target.exists():
            print(f"⚠️ Target {target} not found")
            continue
            
        print(f"Scanning: {target}")
        results = engine.batch_heal(
            str(target),
            extensions=[".yaml", ".yml"],
            dry_run=True,
            identity_mode="infer",
            fix_tags=True,
            harden=True
        )
        all_results.extend(results)
    
    # Standardize results for comparison (remove transient bits like duration)
    serialized = []
    for r in all_results:
        d = asdict(r)
        # Strip absolute paths to make them portable/stable
        d['file_path'] = os.path.relpath(d['file_path'], str(workspace))
        # Remove duration as it flickers
        if 'duration' in d: d['duration'] = 0.0
        serialized.append(d)
        
    # Sort by file_path for stable diffing
    serialized.sort(key=lambda x: x['file_path'])
    
    baseline_path = workspace / "tests" / "pre_refactor_baseline.json"
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2)
        
    print(f"✅ Baseline captured to {baseline_path}")
    print(f"📊 Total Files: {len(serialized)}")

if __name__ == "__main__":
    capture()
