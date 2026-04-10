import json
import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yamlr.core.pipeline import HealingPipeline


def run_toxic_audit_in_process():
    root_dir = Path(__file__).parent.parent.resolve()
    corpus_dir = root_dir / "tests/corpus/toxic"
    catalog_path = root_dir / "catalog" / "k8s_v1_distilled.json"

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    pipeline = HealingPipeline(catalog)

    files = list(corpus_dir.glob("*.yaml"))
    files.sort()
    target_files = files[:100]

    print(f"Healing {len(target_files)} toxic files in-process...")

    success_count = 0
    crash_count = 0

    for i, f in enumerate(target_files):
        try:
            content = f.read_text(encoding="utf-8")
            result = pipeline.heal(content)

            # Verify status is SUCCESS (even if health score is low, we reconstructed)
            if result.status.value == "SUCCESS":
                success_count += 1

            if (i + 1) % 10 == 0:
                print(f"Progress: {i + 1}/100...")
        except Exception as e:
            print(f"CRASH on {f.name}: {e}")
            crash_count += 1

    print("\n--- TOXIC AUDIT RESULTS ---")
    print(f"Total Files Tested: {len(target_files)}")
    print(f"Successfully Reconstructed: {success_count}")
    print(f"Crashes: {crash_count}")
    print(f"Recovery Rate: {(success_count / len(target_files)) * 100:.1f}%")


if __name__ == "__main__":
    run_toxic_audit_in_process()
