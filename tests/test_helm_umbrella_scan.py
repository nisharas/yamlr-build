"""Tests for Helm chart scanning with templates, values variants, and subcharts."""
import os
import tempfile

import pytest

from yamlr.core.scanner import scan_helm_chart


def test_helm_chart_fallback_subcharts(monkeypatch):
    """Verify scan_helm_chart discovers templates and subcharts even if helm template CLI fails."""
    # Force helm command to fail
    import subprocess
    real_run = subprocess.run
    def mock_run(cmd, *args, **kwargs):
        if cmd[0] == "helm":
            class MockProc:
                returncode = 1
                stdout = ""
                stderr = "mock helm failure"
            return MockProc()
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create chart structure
        chart_dir = os.path.join(tmpdir, "mychart")
        templates_dir = os.path.join(chart_dir, "templates")
        charts_dir = os.path.join(chart_dir, "charts")
        subchart_dir = os.path.join(charts_dir, "subservice")
        sub_templates = os.path.join(subchart_dir, "templates")
        os.makedirs(templates_dir)
        os.makedirs(sub_templates)

        # Write values.yaml
        with open(os.path.join(chart_dir, "values.yaml"), "w", encoding="utf-8") as f:
            f.write("replicaCount: 3\n")

        # Write main template
        with open(os.path.join(templates_dir, "deployment.yaml"), "w", encoding="utf-8") as f:
            f.write("""apiVersion: apps/v1
kind: Deployment
metadata:
  name: main-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: main
  template:
    metadata:
      labels:
        app: main
    spec:
      containers:
        - name: app
          image: nginx:1.21.0
""")

        # Write subchart template
        with open(os.path.join(sub_templates, "service.yaml"), "w", encoding="utf-8") as f:
            f.write("""apiVersion: v1
kind: Service
metadata:
  name: sub-svc
spec:
  ports:
    - port: 80
""")

        results = list(scan_helm_chart(chart_dir, schemas=[]))
        # Should have found results from main chart and subchart
        assert len(results) >= 2
        paths = [r.file_path for r in results]
        assert any("deployment.yaml" in p for p in paths)
        assert any("service.yaml" in p for p in paths)
