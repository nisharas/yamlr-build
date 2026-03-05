from yamlr.core.pipeline import HealingPipeline
import json

def reproduce():
    k8s_distilled = json.load(open('catalog/k8s_v1_distilled.json'))
    pipeline = HealingPipeline(catalog=k8s_distilled)
    
    # containers: name: nginx
    # 'containers' is a list, but children are map keys
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
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reproduce()
