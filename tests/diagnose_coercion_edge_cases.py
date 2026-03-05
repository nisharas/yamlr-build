import unittest
import os
from yamlr.core.engine import YamlrEngine

class TestCoercionEdgeCases(unittest.TestCase):
    def setUp(self):
        self.engine = YamlrEngine.quick(os.getcwd())
        self.pipeline = self.engine.pipeline

    def test_numeric_label_coercion(self):
        # K8s labels MUST be strings. If a user provides a number,
        # we should ideally coerce it to a string to be 'Google-quality'.
        yaml_content = """
apiVersion: v1
kind: Pod
metadata:
  name: numeric-label-test
  labels:
    version: 1.0
    app: 123
spec:
  containers:
  - name: nginx
    image: nginx
"""
        result = self.pipeline.heal(yaml_content)
        # Current behavior: might leave them as numbers if they were numbers in YAML.
        # But if they come from shards, they might be strings already? 
        # Shard.value is parsed by ruamel.yaml in the Scanner.
        print(f"DEBUG Contents:\n{result.content}")
        
    def test_configmap_data_coercion(self):
        # ConfigMap data values MUST be strings.
        yaml_content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: cm-test
data:
  ENABLE_CACHE: true
  RETRY_COUNT: 5
"""
        result = self.pipeline.heal(yaml_content)
        print(f"DEBUG CM Contents:\n{result.content}")

if __name__ == "__main__":
    unittest.main()
