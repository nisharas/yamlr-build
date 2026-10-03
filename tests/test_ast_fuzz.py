import difflib
import os
from unittest.mock import patch

import pytest
import yamlr_native

COMPLEX_YAML_FIXTURE = """# Core deployment for api-server
# Do not change the label matchers!
apiVersion: apps/v1
kind: Deployment
metadata:
  name: &app_name api-server # Anchor test
  labels:
    app: *app_name # Alias test
    env: dev # WE WILL MUTATE THIS
spec:
  replicas: 3
  selector:
    matchLabels:
      app: *app_name
  template:
    metadata:
      labels:
        app: *app_name
        # Keep this comment
        env: dev
    spec:
      containers:
        - name: main
          image: "nginx:1.24" # Upgraded for CVE-2023-XYZ
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
"""

def test_ast_preservation_atomic():
    """Verifies that atomic fixes preserve comments, anchors, and formatting."""
    test_file = "temp_complex_fixture.yaml"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(COMPLEX_YAML_FIXTURE)
        
    try:
        success = yamlr_native.native_apply_fix_atomic(
            test_file,
            "metadata.labels.env",
            "prod",
            None,
            None
        )
        assert success is True, "Native apply fix failed"
        
        with open(test_file, "r", encoding="utf-8") as f:
            modified_content = f.read()
            
        original_lines = COMPLEX_YAML_FIXTURE.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(original_lines, modified_lines, n=0))
        
        additions = [line for line in diff if line.startswith('+') and not line.startswith('+++')]
        deletions = [line for line in diff if line.startswith('-') and not line.startswith('---')]
        
        assert len(additions) == 1, f"Expected 1 addition, got {len(additions)}: {additions}"
        assert len(deletions) == 1, f"Expected 1 deletion, got {len(deletions)}: {deletions}"
        
        assert "# Anchor test" in modified_content
        assert "# Alias test" in modified_content
        assert "*app_name" in modified_content
        assert "# Keep this comment" in modified_content
        assert 'image: "nginx:1.24" # Upgraded for CVE-2023-XYZ' in modified_content
        
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
