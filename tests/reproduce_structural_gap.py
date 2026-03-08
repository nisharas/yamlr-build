from yamlr.core.pipeline import HealingPipeline

def reproduce():
    pipeline = HealingPipeline()
    # containers SHOULD be a list, but here it's a map
    yaml_content = """
apiVersion: v1
kind: Pod
metadata:
  name: structural-test
spec:
  containers:
    name: nginx
    image: nginx
"""
    print("--- Original ---")
    print(yaml_content)
    
    try:
        result = pipeline.heal(yaml_content)
        print("--- Healed ---")
        print(result.content)
    except Exception as e:
        print(f"FAILED with error: {e}")

if __name__ == "__main__":
    reproduce()
