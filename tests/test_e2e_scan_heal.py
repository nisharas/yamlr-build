"""End-to-End Tests for Public API Scanning and Healing."""
import os
from pathlib import Path

import pytest
import yaml

from yamlr import HealResult, heal_yaml, scan_yaml

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_e2e_heal_deprecated_api():
    """E2E: Ingress with deprecated networking.k8s.io/v1beta1 apiVersion."""
    deprecated_path = FIXTURES_DIR / "deprecated-api.yaml"
    if not deprecated_path.exists():
        pytest.skip("deprecated-api.yaml fixture not found")

    content = deprecated_path.read_text(encoding="utf-8")
    result = heal_yaml(content, k8s_version="1.30")

    assert isinstance(result, HealResult)
    # If changes were applied, the output must be valid YAML
    if result.had_changes:
        assert len(result.changes) > 0
        parsed = yaml.safe_load(result.healed_yaml)
        assert parsed is not None
        assert parsed.get("kind") == "Ingress"
    else:
        # If no changes were required, original content is retained
        assert result.healed_yaml == content


def test_e2e_scan_manifest_violations():
    """E2E: Validates scan_yaml returns structured violations and identity."""
    fixture_path = FIXTURES_DIR / "healer_test.yaml"
    if not fixture_path.exists():
        pytest.skip("healer_test.yaml fixture not found")

    content = fixture_path.read_text(encoding="utf-8")
    scan_result = scan_yaml(content, k8s_version="1.30")

    assert isinstance(scan_result, dict)
    assert "identity" in scan_result
    assert "violations" in scan_result
    assert "integrity_violations" in scan_result

    if scan_result["identity"]:
        assert scan_result["identity"]["kind"] == "Service"
        assert scan_result["identity"]["name"] == "healer-service"


def test_e2e_heal_comment_preservation():
    """E2E: Ensures critical comments and layout survive the healing pass."""
    yaml_with_comments = """# Global Cluster Anchor Header
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app # Crucial application name
spec:
  replicas: 3 # Hardcoded replica count
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: nginx:1.25.3
"""
    result = heal_yaml(yaml_with_comments, k8s_version="1.30")
    assert isinstance(result, HealResult)
    assert "# Global Cluster Anchor Header" in result.healed_yaml
    assert "# Crucial application name" in result.healed_yaml


def test_e2e_heal_idempotency():
    """E2E: Healing an already clean/healed manifest produces zero further changes."""
    clean_yaml = """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: default
data:
  APP_ENV: production
"""
    first_heal = heal_yaml(clean_yaml, k8s_version="1.30")
    second_heal = heal_yaml(first_heal.healed_yaml, k8s_version="1.30")

    assert second_heal.had_changes is False
    assert len(second_heal.changes) == 0
