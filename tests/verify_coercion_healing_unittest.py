import unittest
import os
from yamlr.core.engine import YamlrEngine

class TestTypeCoercionHealing(unittest.TestCase):
    def setUp(self):
        # Use quick() to load default catalog
        self.engine = YamlrEngine.quick(os.getcwd())
        self.pipeline = self.engine.pipeline

    def test_replicas_coercion(self):
        # Deployment with stringified replicas: "3"
        yaml_content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: type-test
spec:
  replicas: "3"
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx
"""
        result = self.pipeline.heal(yaml_content)
        
        # Should be coerced to integer 3 (no quotes)
        self.assertIn("replicas: 3", result.content)
        # Verify it's not a string "3"
        self.assertNotIn("replicas: \"3\"", result.content)
        self.assertNotIn("replicas: '3'", result.content)

    def test_boolean_coercion(self):
        # HostNetwork as string "true"
        yaml_content = """
apiVersion: v1
kind: Pod
metadata:
  name: bool-test
spec:
  hostNetwork: "true"
  containers:
  - name: nginx
    image: nginx
"""
        result = self.pipeline.heal(yaml_content)
        self.assertIn("hostNetwork: true", result.content)

    def test_int_or_string_preservation(self):
        # targetPort can be int or string, should NOT be coerced
        yaml_content = """
apiVersion: v1
kind: Service
metadata:
  name: target-port-test
spec:
  selector:
    app: nginx
  ports:
  - protocol: TCP
    port: 80
    targetPort: "8080"
"""
        result = self.pipeline.heal(yaml_content)
        # Should remain a string because of x-kubernetes-int-or-string
        self.assertIn("targetPort: '8080'", result.content)

    def test_numeric_label_to_string_coercion(self):
        # Numeric labels MUST be strings in K8s
        yaml_content = """
apiVersion: v1
kind: Pod
metadata:
  name: label-test
  labels:
    version: 1.0
spec:
  containers:
  - name: nginx
    image: nginx
"""
        result = self.pipeline.heal(yaml_content)
        # 1.0 (float) should become "1.0" (string)
        self.assertIn("version: '1.0'", result.content) # ruamel usually adds quotes for numbers-as-strings

if __name__ == "__main__":
    unittest.main()
