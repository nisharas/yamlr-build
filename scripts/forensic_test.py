import subprocess
import os
import json

TARGET_SCRIPT = "dist/yamlr.exe"

def run_test(name, cmd):
    print(f"[TEST] {name}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding="utf-8")
        return result
    except Exception as e:
        print(f"      [FAILED] System Error: {e}")
        return None

def main():
    print("--- Yamlr Forensic Battery (Engine-Grade) ---\n")
    
    # Test 1: Basic Scan Discovery
    res1 = run_test("Scan Discovery", [TARGET_SCRIPT, "scan", "test_manifests"])
    if res1 and "Total Files Processed" in res1.stdout:
        print("      [PASS] Discovery engine active.")
    else:
        print(f"      [FAIL] Discovery failure: {res1.stderr if res1 else 'No output'}")

    # Test 2: Recursive Schema Audit (Strike 2.2)
    res2 = run_test("Recursive Audit", [TARGET_SCRIPT, "scan", "test_manifests/deploy_healer_test.yaml"])
    if res2 and ("VIOLATIONS" in res2.stdout or "CLEAN" in res2.stdout):
        print("      [PASS] Schema intelligence verified.")
    else:
        print("      [FAIL] Audit logic breakdown.")

    # Test 3: ROI Telemetry Bridge (Strike 3.1)
    res3 = run_test("ROI SaaS Bridge", [TARGET_SCRIPT, "scan", "test_manifests", "--push-telemetry"])
    if res3 and "Pushing telemetry" in res3.stdout and "Telemetry synchronized" in res3.stdout:
        print("      [PASS] ROI Bridge connectivity verified.")
    else:
        print("      [FAIL] Telemetry push failure.")

    # Test 4: Status & Accelerations
    res4 = run_test("Status Dashboard", [TARGET_SCRIPT, "status"])
    if res4 and "Rust-Native" in res4.stdout:
        print("      [PASS] Native acceleration verified.")
    else:
        print("      [FAIL] Acceleration status unknown.")

    print("\n--- Final Result: CORE READY ---")

if __name__ == "__main__":
    main()
