import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# Setup PYTHONPATH and Encoding for testing
@pytest.fixture(scope="session", autouse=True)
def setup_env():
    # Adjusted to point to the correct src location relative to tests/pro/reconciliation
    src_dir = str(Path(__file__).parent.parent.parent.parent / "src")
    os.environ["PYTHONPATH"] = src_dir + os.pathsep + os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["YAMLR_CLASSIC"] = "1"
    os.environ["YAMLR_TEST"] = "true"
    os.environ["YAMLR_INTERNAL_TEST_MODE"] = "true"
    os.environ["YAMLR_DISABLE_NATIVE"] = "1"


def run_yamlr(args):
    """Helper to run yamlr CLI with PYTHONPATH set."""
    cmd = [sys.executable, "-m", "yamlr.cli.main"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ, encoding="utf-8")
    return result


def test_complement_mode_checkov_cli(tmp_path):
    """
    E2E Test: yamlr heal --complement-mode checkov:report.json

    Why: Verifies that the CLI correctly bridges to the ReconciliationEngine
         and applies fixes to the target file.
    """
    # 1. Setup misconfigured YAML in the tmp_path
    # We must ensure the file_path in the report matches the workspace-relative path
    yaml_content = """
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
    manifest_path.write_text(yaml_content, encoding="utf-8")

    # 2. Setup Checkov report (Mocked)
    # The file_path in Checkov reports is usually absolute or relative to the scan root.
    # Our ReconciliationEngine normalizes it.
    checkov_report = {
        "results": {
            "failed_checks": [
                {
                    "check_id": "CKV_K8S_21",
                    "check_name": "Ensure the container is not run as root",
                    "file_path": "/deploy.yaml",
                    "resource": "Pod.default.security-vuln",
                }
            ]
        }
    }
    report_path = tmp_path / "checkov.json"
    report_path.write_text(json.dumps(checkov_report), encoding="utf-8")

    # 3. Run CLI heal with Complement Mode
    # We run from the tmp_path to ensure correct workspace detection
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "yamlr.cli.main",
            "heal",
            "deploy.yaml",
            "--complement-mode",
            f"checkov:{report_path}",
            "-y",
            "--harden",
            "--verbose",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=os.environ,
        encoding="utf-8",
    )

    # Debug output if it fails
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)

    assert result.returncode == 0

    # Verify the log message from YamlrEngine (in verbose mode)
    combined_output = result.stdout + result.stderr
    assert "Complement Mode" in combined_output
    assert "Reconciled 1 external findings" in combined_output

    # 4. Verify the file was actually modified (Remediation confirmed)
    healed_content = manifest_path.read_text(encoding="utf-8")
    assert "runAsNonRoot: true" in healed_content
    # Ensure it didn't just wipe the file
    assert "name: web" in healed_content


def test_complement_mode_kubeconform_cli(tmp_path):
    """
    E2E Test: yamlr scan --complement-mode kubeconform:results.json

    Why: Verifies that structural findings from Kubeconform are correctly ingested and displayed.
    """
    yaml_content = 'apiVersion: v1\nkind: Service\nmetadata:\n  name: my-svc\nspec:\n  ports: "not-a-list"'
    manifest_path = tmp_path / "service.yaml"
    manifest_path.write_text(yaml_content, encoding="utf-8")

    # Mock Kubeconform output (one finding)
    kubeconform_findings = [
        {
            "filename": "service.yaml",
            "kind": "Service",
            "name": "my-svc",
            "version": "v1",
            "status": "Invalid",
            "errors": ["Invalid type. Expected: [array,null], given: string"],
        }
    ]
    report_path = tmp_path / "kubeconform.json"
    report_path.write_text(json.dumps(kubeconform_findings), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "yamlr.cli.main",
            "scan",
            "service.yaml",
            "--complement-mode",
            f"kubeconform:{report_path}",
            "--verbose",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=os.environ,
        encoding="utf-8",
    )

    assert result.returncode in [0, 1]  # Scan may return 1 if findings are found
    combined_output = result.stdout + result.stderr
    assert "reconciled" in combined_output.lower()
    assert "schema/type-mismatch" in combined_output or "Invalid type" in combined_output
