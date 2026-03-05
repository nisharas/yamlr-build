import sys
import json
import os
from pathlib import Path
from dataclasses import asdict
import difflib

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.engine import YamlrEngine

def verify():
    print("🔬 Verifying Post-Refactor Parity (Scanner)...")
    workspace = Path(__file__).parent.parent
    engine = YamlrEngine.quick(str(workspace))
    
    baseline_path = workspace / "tests" / "pre_refactor_baseline.json"
    if not baseline_path.exists():
        print(f"❌ Baseline {baseline_path} not found")
        sys.exit(1)
        
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    targets = [workspace / "tests" / "fixtures", workspace / "tests" / "corpus"]
    all_results = []
    for target in targets:
        if not target.exists(): continue
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

    def normalize_list(results):
        normalized = []
        for r in results:
            d = r if isinstance(r, dict) else asdict(r)
            # Normalize path
            if 'file_path' in d and os.path.isabs(d['file_path']):
                d['file_path'] = os.path.relpath(d['file_path'], str(workspace))
            
            # Normalize non-deterministic fields
            d['timestamp'] = 0.0
            d['processing_time_seconds'] = 0.0
            if 'logic_logs' in d: d['logic_logs'] = [] 
            if 'processing_stats' in d and 'timings' in d['processing_stats']:
                d['processing_stats']['timings'] = {}
            if 'duration' in d: d['duration'] = 0.0
            
            normalized.append(d)
        normalized.sort(key=lambda x: x.get('file_path', ""))
        return normalized

    normalized_baseline = normalize_list(baseline)
    normalized_current = normalize_list(all_results)
    
    # Byte-level JSON comparison
    baseline_str = json.dumps(normalized_baseline, indent=2)
    current_str = json.dumps(normalized_current, indent=2)
    
    if baseline_str == current_str:
        print("✨ 100% FUNCTIONAL PARITY MAINTAINED ✨")
    else:
        print("❌ PARITY VIOLATION DETECTED!")
        # Show a snippet of the diff
        diff = difflib.unified_diff(
            baseline_str.splitlines(),
            current_str.splitlines(),
            fromfile='baseline',
            tofile='current',
            n=5
        )
        print("\n".join(list(diff)[:50]))
        sys.exit(1)

if __name__ == "__main__":
    verify()
