"""Unit tests for OPA and Kyverno policy ingestion."""
import json
import os

import pytest

from yamlr.core.stages.policy_ingestion_stage import PolicyIngestionStage


def test_parse_opa_violations(tmp_path):
    opa_data = {
        "violations": [
            {
                "constraint": "k8srequiredlabels",
                "resource": {"kind": "Deployment", "name": "my-deploy"},
                "message": "Missing required label: app"
            }
        ]
    }
    report_file = tmp_path / "opa-report.json"
    report_file.write_text(json.dumps(opa_data), encoding="utf-8")

    violations = PolicyIngestionStage._parse_opa(opa_data)
    assert len(violations) == 1
    assert violations[0]["kind"] == "Deployment"
    assert violations[0]["name"] == "my-deploy"


def test_parse_kyverno_violations(tmp_path):
    kyverno_data = {
        "results": [
            {
                "policy": "disallow-latest-tag",
                "resources": [{"kind": "Pod", "name": "test-pod"}],
                "message": "Using latest tag is disallowed."
            }
        ]
    }
    violations = PolicyIngestionStage._parse_kyverno(kyverno_data)
    assert len(violations) == 1
    assert violations[0]["kind"] == "Pod"
    assert violations[0]["name"] == "test-pod"
