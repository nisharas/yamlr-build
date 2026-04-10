import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_mutation_audit():
    """
    Native Mutation Auditor for Yamlr.

    Why: To verify test sensitivity without relying on brittle third-party
         mutation libraries on Windows.
    """
    src_file = Path("src/yamlr/core/scoring.py")
    backup_file = Path("src/yamlr/core/scoring.py.bak")
    test_file = Path("tests/test_simple_scoring.py")

    # 1. Ensure clean state
    if backup_file.exists():
        shutil.copy2(backup_file, src_file)
    else:
        shutil.copy2(src_file, backup_file)

    try:
        print("--- Mutation Audit: Starting ---")

        # Scenario A: Mutate Critical Penalty
        print("\n[Scenario A] Mutating 'penalty = 25' -> 'penalty = 0' (CRITICAL)")
        with open(src_file, "r") as f:
            content = f.read()

        mutated_content = content.replace("penalty = 25", "penalty = 0")
        with open(src_file, "w") as f:
            f.write(mutated_content)

        # Run test
        env = os.environ.copy()
        env["PYTHONPATH"] = "src;."
        result = subprocess.run(["python", "-m", "pytest", str(test_file)], env=env, capture_output=True, text=True)

        if result.returncode != 0:
            print("SUCCESS: Mutation KILLED (Test failed as expected)")
        else:
            print("FAILURE: Mutation SURVIVED (Test passed despite a major bug!)")

        # Scenario B: Mutate Default Warning Penalty
        print("\n[Scenario B] Mutating 'penalty = 3' -> 'penalty = 300' (WARNING)")
        with open(src_file, "r") as f:
            content = f.read()
        # Restore first
        content = content.replace("penalty = 0", "penalty = 25")
        mutated_content = content.replace("penalty = 3", "penalty = 300")
        with open(src_file, "w") as f:
            f.write(mutated_content)

        result = subprocess.run(["python", "-m", "pytest", str(test_file)], env=env, capture_output=True, text=True)

        if result.returncode != 0:
            print("SUCCESS: Mutation KILLED (Test failed as expected)")
        else:
            print("FAILURE: Mutation SURVIVED (Test passed despite a major bug!)")

    finally:
        # Restore original
        print("\n--- Restoring original source ---")
        shutil.copy2(backup_file, src_file)
        backup_file.unlink()


if __name__ == "__main__":
    run_mutation_audit()
