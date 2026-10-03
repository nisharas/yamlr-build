"""Unit tests for Fleet-Wide Kubernetes Deprecation Upgrades."""
import pytest

from yamlr.core.stages.deprecation_upgrade_stage import DEPRECATION_MAP, DeprecationUpgradeStage


def test_deprecation_map_entries():
    assert ("extensions/v1beta1", "Deployment") in DEPRECATION_MAP
    assert DEPRECATION_MAP[("extensions/v1beta1", "Deployment")] == "apps/v1"
    assert DEPRECATION_MAP[("networking.k8s.io/v1beta1", "Ingress")] == "networking.k8s.io/v1"
    assert DEPRECATION_MAP[("policy/v1beta1", "PodDisruptionBudget")] == "policy/v1"


def test_execute_fleet_upgrade_preview(tmp_path):
    deprecated_yaml = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: legacy-app
spec:
  replicas: 1
"""
    manifest_path = tmp_path / "legacy.yaml"
    manifest_path.write_text(deprecated_yaml, encoding="utf-8")

    records = DeprecationUpgradeStage.execute_fleet_upgrade(
        target_path=str(tmp_path),
        target_k8s_version="1.30",
        apply=False
    )
    assert len(records) == 1
    assert records[0]["kind"] == "Deployment"
    assert records[0]["old_api"] == "extensions/v1beta1"
    assert records[0]["new_api"] == "apps/v1"
    # Preview mode: file on disk unchanged
    assert "extensions/v1beta1" in manifest_path.read_text(encoding="utf-8")
