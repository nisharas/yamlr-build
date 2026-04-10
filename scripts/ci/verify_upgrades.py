import os

from yamlr.engine import HealConfig, YamlrEngine


def test_sdk_and_receipts():
    print("Testing SDK Entry Point...")
    try:
        engine = YamlrEngine.quick(".")
        print("✅ SDK: YamlrEngine.quick works.")
    except Exception as e:
        print(f"❌ SDK: YamlrEngine.quick failed: {e}")
        return

    print("\nTesting DNA Receipt Embedding...")
    raw_yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
  - name: web
    image: nginx:latest
"""
    config = HealConfig(generate_receipts=True, embed_receipt=True, file_path="test.yaml")
    # Enable pro capability for generate_evidence manually for test
    config.capabilities.can_generate_evidence = True

    # result = engine.heal(raw_yaml, config=config)
    result = engine.pipeline.heal(raw_yaml, config=config)

    if result.status == "SUCCESS":
        print("✅ Healing: Done.")
        if "[Yamlr-Receipt-of-Integrity]" in result.content:
            print("✅ Receipt: Embedded in content.")
            print("--- Content Tail ---")
            print("\n".join(result.content.splitlines()[-3:]))
        else:
            print("❌ Receipt: NOT found in content.")
            # print(result.content)
    else:
        print(f"❌ Healing failed: {result.error_message}")


if __name__ == "__main__":
    test_sdk_and_receipts()
