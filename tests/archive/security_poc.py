#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from yamlr.core.utils import get_hardened_yaml


def test_billion_laughs():
    print("--- Testing Billion Laughs Resistance ---")
    # 51 aliases (Limit is 50)
    bomb = "a: &a1 [1,2,3]\n"
    for i in range(2, 52):
        bomb += f"a{i}: &a{i} [*a{i - 1}, *a{i - 1}]\n"
    bomb += "result: *a51"

    parser = get_hardened_yaml(typ="rt")
    try:
        parser.load(bomb)
        print("FAIL: Parser allowed 51 aliases!")
    except Exception as e:
        print(f"SUCCESS: Parser blocked the bomb. Error: {str(e)[:100]}...")


def test_option_injection_logic():
    print("\n--- Testing OPA Option Injection Logic ---")
    # Mocking the vulnerable logic in opa_adapter.py
    policy = "--help"

    def is_bundle(path):
        return path.endswith(".tar.gz") or os.path.isdir(path)

    is_b = is_bundle(policy)
    eval_flag = "--bundle" if is_b else "--data"

    # Simulate command construction
    cmd = ["opa", "eval", "--input", "tmp.json", eval_flag, policy, "data.yamlr.deny.violation"]
    print(f"Constructed Command: {' '.join(cmd)}")

    if policy.startswith("-"):
        print("VULNERABILITY: User-controlled 'policy' can inject flags (e.g., --help) into the OPA command.")
        print("Even with shell=False, the 'opa' binary will interpret '--help' as a flag.")


if __name__ == "__main__":
    test_billion_laughs()
    test_option_injection_logic()
