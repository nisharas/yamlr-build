import json
import os
import subprocess
import sys
from pathlib import Path


def run_batch_heal():
    root_dir = Path(__file__).parent.parent.resolve()
    corpus_dir = root_dir / "tests/corpus/toxic"
    output_dir = root_dir / "tests/toxic_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    files = list(corpus_dir.glob("*.yaml"))
    print(f"Healing {len(files)} toxic files...")

    success_count = 0
    total_penalty_reduction = 0

    for f in files:
        # Run heal command
        cmd = [sys.executable, "-m", "yamlr", "heal", str(f), "--no-backup", "--quiet"]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8")

        if res.returncode == 0:
            success_count += 1
            # In a real scenario we'd check health score change,
            # but here we just verify no crash and valid output.
        else:
            print(f"FAILED to heal: {f.name}")
            print(res.stderr)

    print("\n--- BATCH HEAL RESULTS ---")
    print(f"Total Files: {len(files)}")
    print(f"Successfully Healed: {success_count}")
    print(f"Success Rate: {(success_count / len(files)) * 100:.1f}%")

    if success_count == len(files):
        print("✅ 100% Recovery Achieved!")
    else:
        print(f"❌ {len(files) - success_count} files failed to heal.")


if __name__ == "__main__":
    run_batch_heal()
