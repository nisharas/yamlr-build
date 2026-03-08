import sys
import os
from pathlib import Path
import json

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yamlr.core.engine import YamlrEngine

def test_wedge_gauntlet():
    print("🚀 Starting Wedge Gauntlet UAT...")
    
    workspace = Path(__file__).parent.parent
    test_file = workspace / "tests" / "test_wedge_gauntlet.yaml"
    
    # [Task] Verify Engine.quick()
    print("--- Testing YamlrEngine.quick() ---")
    try:
        engine = YamlrEngine.quick(str(workspace))
        print("✅ YamlrEngine.quick() initialized successfully")
    except Exception as e:
        print(f"❌ YamlrEngine.quick() failed: {e}")
        return

    # [Task] Run Scan (Stage 3 + Stage 6)
    print("\n--- Testing Scan & Heal (Typo + Coercion + Structure) ---")
    result = engine.audit_and_heal_file(
        str(test_file),
        dry_run=True,
        identity_mode="infer"
    )

    print(f"Result type: {type(result)}")
    print(f"Result attributes: {dir(result)}")
    print(f"Status: {result.status}")
    print(f"Findings: {len(result.findings)}")
    for f in result.findings:
        print(f"  - {f}")

    healed_content = result.healed_content
    print("\n--- Healed Content Preview ---")
    print(healed_content)

    # Verification Assertions
    print("\n--- Assertions ---")
    passed = True
    
    if "replicas: 3" in healed_content:
        print("✅ Typo 'replicass' -> 'replicas' FIXED and coerced to integer")
    else:
        print("❌ Typo 'replicass' or type coercion failed")
        passed = False

    if "imagePullSecrets:" in healed_content and "- name: my-secret" in healed_content:
        print("✅ 'imagePullSecret' singular -> 'imagePullSecrets' FIXED and wrapped in list")
    else:
        print("❌ 'imagePullSecret' wrapping or typo fix failed")
        passed = False

    if "ports:" in healed_content and "- containerPort: 8080" in healed_content:
        print("✅ 'ports' map -> list FIXED and containerPort coerced to integer")
    else:
        print("❌ 'ports' structural fix or coercion failed")
        passed = False

    if passed:
        print("\n✨ WEDGE GAUNTLET PASSED ✨")
    else:
        print("\n⚠️ WEDGE GAUNTLET FAILED ⚠️")

if __name__ == "__main__":
    test_wedge_gauntlet()
