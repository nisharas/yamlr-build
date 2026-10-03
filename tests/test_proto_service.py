import pytest

from yamlr.proto_service import ManifestService


def test_proto_service_scan_valid():
    svc = ManifestService()
    req = {
        "content": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 1
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
        image: nginx:1.25.0
""",
        "file_path": "in-memory.yaml",
        "target_k8s_version": "1.30",
    }
    resp = svc.scan_document(req)
    assert resp["status"] in ["passed", "failed"]
    assert "health_score" in resp
    assert "duration_ms" in resp


def test_proto_service_heal_idempotent():
    svc = ManifestService()
    content = """# Comment
apiVersion: v1
kind: Service
metadata:
  name: my-svc
spec:
  ports:
  - port: 80
    targetPort: 80
"""
    req = {"content": content, "dry_run": True}
    resp = svc.heal_document(req)
    assert resp["healed_content"] == content
    assert resp["mutated"] is False
