import json
import os
from pathlib import Path

import pytest

from yamlr.core.engine import YamlrEngine
from yamlr.core.pipeline.models import HealStatus
from yamlr.pro.reconciliation.engine import ReconciliationEngine


def test_checkov_to_healing_integration(tmp_path):
    """
    Test the full flow: Checkov JSON -> Reconciliation -> Healing Pipeline -> Remediation.

    Why: To ensure Checkov findings are correctly mapped to internal Fix IDs
         and actually trigger the corresponding the healing mutations.
    """
    # 1. Create a misconfigured YAML file
    # This one has a container running as root (securityContext missing runAsNonRoot)
    misconfigured_yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: security-vuln
spec:
  containers:
  - name: web
    image: nginx
    securityContext:
      privileged: false
"""
    manifest_path = tmp_path / "deploy.yaml"
    manifest_path.write_text(misconfigured_yaml)

    # 2. Create a mock Checkov JSON report pointing to this file
    # CKV_K8S_21: Ensure the container is not run as root
    checkov_report = {
        "check_type": "kubernetes",
        "results": {
            "passed_checks": [],
            "failed_checks": [
                {
                    "check_id": "CKV_K8S_21",
                    "check_name": "Ensure the container is not run as root",
                    "file_path": "/deploy.yaml",
                    "file_line_range": [1, 10],
                    "resource": "Pod.default.security-vuln",
                    "status": "FAILED",
                }
            ],
            "skipped_checks": [],
        },
    }
    report_path = tmp_path / "checkov_results.json"
    report_path.write_text(json.dumps(checkov_report))

    # 3. Initialize Engine and Run Scan with Complement Mode
    # We use YAMLR_DISABLE_NATIVE=1 to ensure we use the Python parser for the test
    os.environ["YAMLR_DISABLE_NATIVE"] = "1"

    engine = YamlrEngine(workspace_path=str(tmp_path))

    # Reconcile findings
    re_engine = ReconciliationEngine(str(tmp_path))
    external_findings = re_engine.reconcile_all([f"checkov:{report_path}"])

    # Group findings
    external_findings_map = {"deploy.yaml": external_findings}

    # Run healing
    results = engine.batch_heal(
        root_path=str(tmp_path),
        dry_run=False,  # We want to see the healed content
        external_findings_map=external_findings_map,
        harden=True,  # Ensure security hardening is enabled
    )

    # 4. Assertions
    assert len(results) == 1
    res = results[0]
    assert res.success

    # Verify that CKV_K8S_21 was handled
    # It should have mapped to 'security/run-as-non-root' Rule ID
    finding_ids = []
    for f in res.findings:
        if isinstance(f, dict):
            finding_ids.append(f.get("rule_id"))
        else:
            finding_ids.append(getattr(f, "rule_id", None))

    assert "security/run-as-non-root" in finding_ids

    # Check if the forensic anchor (analyzer name) is preserved
    found_anchor = False
    for f in res.findings:
        fields = []
        if isinstance(f, dict):
            fields = [f.get("message", ""), f.get("description", ""), f.get("analyzer_name", "")]
        else:
            fields = [getattr(f, "message", ""), getattr(f, "description", ""), getattr(f, "analyzer_name", "")]

        if any("Checkov (CKV_K8S_21)" in (field or "") for field in fields):
            found_anchor = True
            break

    assert found_anchor

    # Verify the content was actually healed
    healed_yaml = res.healed_content
    assert "runAsNonRoot: true" in healed_yaml
    assert "runAsUser:" in healed_yaml  # Should also add runAsUser if using standard non-root fix


def test_kubeconform_to_healing_integration(tmp_path):
    """
    Test Kubeconform validation error mapping to structural healing.
    """
    # 1. Create a structurally invalid YAML
    # Invalid replicas type (string instead of int)
    invalid_yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: "3"
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx
"""
    manifest_path = tmp_path / "app.yaml"
    manifest_path.write_text(invalid_yaml)

    # 2. Mock Kubeconform report
    kubeconform_report = [
        {
            "filename": "app.yaml",
            "kind": "Deployment",
            "name": "web-deploy",
            "version": "apps/v1",
            "status": "error",
            "errors": ["Invalid type. Expected: integer, given: string"],
        }
    ]
    report_path = tmp_path / "kubeconform.json"
    report_path.write_text(json.dumps(kubeconform_report))

    # 3. Run reconciliation and scan
    engine = YamlrEngine(workspace_path=str(tmp_path))
    re_engine = ReconciliationEngine(str(tmp_path))
    external_findings = re_engine.reconcile_all([f"kubeconform:{report_path}"])

    external_findings_map = {"app.yaml": external_findings}

    results = engine.batch_heal(root_path=str(tmp_path), dry_run=False, external_findings_map=external_findings_map)

    # 4. Assertions
    assert len(results) == 1
    res = results[0]

    # Map 'Invalid type' usually goes to 'type_reconciliation' if mapped
    # Check if any finding has correct fix_id
    healed_yaml = res.healed_content
    # Depending on the Healer, it should fix replicas: "3" to replicas: 3
    assert "replicas: 3" in healed_yaml
    assert '"3"' not in healed_yaml
