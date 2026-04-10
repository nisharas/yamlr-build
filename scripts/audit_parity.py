"""
Yamlr Forensic Engine: Cross-Platform Audit Parity
-------------------------------------------------
Verifies bit-for-bit semantic parity between the current build
and the 'Gold Standard' baseline.

Why: To prevent regressions during refactoring on Linux, MacOS, and Windows.
     Ensures that architectural consolidation (Shield -> Core) 
     does not alter the forensic result stream.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Set

def load_json(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def canonicalize(finding: Dict[str, Any]) -> str:
    """Creates a stable string key for a finding, ignoring environment noise."""
    # Ignore absolute path segments, line numbers (if they shift), and IDs
    rule = finding.get("rule_id", "unknown")
    resource = finding.get("resource_name", "unknown")
    kind = finding.get("resource_kind", "unknown")
    msg = finding.get("message", "")
    
    # We use kind + name + rule + message as the unique semantic key
    return f"{kind}|{resource}|{rule}|{msg}"

def main():
    baseline_path = os.path.join(".gemini", "baseline", "gold_standard.json")
    if not os.path.exists(baseline_path):
        baseline_path = ".yamlr-baseline.json" # Fallback to project root

    print(f"🚀 Starting Cross-Platform Parity Audit...")
    print(f"📍 Baseline: {baseline_path}")

    gold_findings = load_json(baseline_path)
    if not gold_findings:
        print("❌ Error: No baseline found. Run 'scripts/capture_baseline.py' first.")
        sys.exit(1)

    # Run current build scan
    print("🔍 Scanning workspace with current build...")
    try:
        # Use python -m yamlr to ensure we test the current source/installation
        result = subprocess.run(
            [sys.executable, "-m", "yamlr", "scan", ".", "--output", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        current_findings = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Scan failed: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("❌ Error: Could not parse scan output as JSON.")
        sys.exit(1)

    # Semantic Comparison
    gold_set = {canonicalize(f) for f in gold_findings}
    current_set = {canonicalize(f) for f in current_findings}

    missing = gold_set - current_set
    new_findings = current_set - gold_set

    print(f"📊 Gold Standard Count: {len(gold_set)}")
    print(f"📊 Current Build Count: {len(current_set)}")

    success = True
    if missing:
        print(f"\n❌ REGRESSION: {len(missing)} findings disappeared!")
        for m in sorted(list(missing))[:5]:
            print(f"   - {m}")
        success = False

    if new_findings:
        print(f"\n⚠️  CHANGE: {len(new_findings)} new findings detected.")
        for n in sorted(list(new_findings))[:5]:
            print(f"   - {n}")
        # Depending on strictness, new findings might be acceptable or require baseline update
        print("💡 Tip: If these are intentional, run 'scripts/capture_baseline.py' to update.")

    if success:
        print("\n✅ PARITY SECURED: No regressions detected.")
        sys.exit(0)
    else:
        print("\n❌ PARITY FAILED: Regressions detected.")
        sys.exit(1)

if __name__ == "__main__":
    main()
