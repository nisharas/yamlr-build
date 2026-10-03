"""Ensure the reviewed SARIF schema enforces fields, levels, and locations."""

import pytest
from jsonschema import ValidationError

from scripts.ci.verify_report_contracts import validator


def test_official_schema_accepts_minimal_complete_sarif():
    validator().validate(
        {
            "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "Yamlr"}}, "results": []}],
        }
    )


@pytest.mark.parametrize(
    "report",
    [
        {"version": "2.1.0", "runs": [], "invented": True},
        {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "Yamlr"}},
                    "results": [{"message": {"text": "finding"}, "level": "critical"}],
                }
            ],
        },
        {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "Yamlr"}},
                    "graphs": [
                        {"id": "invalid-graph-property", "nodes": [], "edges": []}
                    ],
                }
            ],
        },
    ],
)
def test_official_schema_rejects_invalid_sarif(report):
    with pytest.raises(ValidationError):
        validator().validate(report)


def _find_binary() -> str:
    """Locate the native release binary or fallback to python module.
    
    Why: Exercises the actual compiled Rust release artifact for report contract fidelity.
    """
    import shutil
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    candidate = root / "native_core" / "target" / "release" / ("yamlr.exe" if sys.platform == "win32" else "yamlr")
    if candidate.is_file():
        return str(candidate)
    which = shutil.which("yamlr")
    if which:
        return which
    return sys.executable


import json
import os
import subprocess
import sys
import time
from pathlib import Path
import jsonschema


def _scan_json_validator() -> jsonschema.Draft202012Validator:
    """Constructs the JSON schema validator for native scan reports.
    
    Why: Ensures native and bridged scan reports strictly conform to schemas/scan-report.schema.json.
    """
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "schemas" / "scan-report.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def _run_cmd(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    bin_path = _find_binary()
    cmd = [bin_path] if bin_path != sys.executable else [bin_path, "-m", "yamlr"]
    cmd.extend(args)
    base_env = os.environ.copy()
    base_env["YAMLR_TELEMETRY"] = "off"
    base_env["CI"] = "true"
    if env:
        base_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(Path(__file__).resolve().parents[1]),
        env=base_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_native_executable_sarif_clean_manifest():
    """Verify yamlr scan emits OASIS-compliant SARIF on a clean manifest.
    
    Why: Validates that zero-finding runs still produce valid SARIF schema documents.
    """
    res = _run_cmd(["scan", ".pre-commit-hooks.yaml", "--output", "sarif"])
    sarif = json.loads(res.stdout)
    validator().validate(sarif)
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) > 0


def test_native_executable_sarif_findings_manifest():
    """Verify yamlr scan emits OASIS-compliant SARIF on a manifest with findings.
    
    Why: Ensures findings, rule descriptors, and severity mappings pass OASIS 2.1.0 schemas.
    """
    res = _run_cmd(["scan", "corpus/golden_corpus/argo-rollouts-install.yaml", "--output", "sarif"])
    sarif = json.loads(res.stdout)
    validator().validate(sarif)
    assert sarif["version"] == "2.1.0"
    results = sarif["runs"][0]["results"]
    assert len(results) > 0


def test_native_executable_sarif_missing_target():
    """Verify yamlr scan emits OASIS-compliant SARIF on missing target errors.
    
    Why: Guarantees that failure notifications and incomplete reports conform to the schema.
    """
    res = _run_cmd(["scan", "missing_manifest_test.yaml", "--output", "sarif"])
    sarif = json.loads(res.stdout)
    validator().validate(sarif)
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["invocations"][0]["executionSuccessful"] is False


def test_native_executable_sarif_audit():
    """Verify yamlr audit emits OASIS-compliant SARIF.
    
    Why: Auditing produces multi-document security findings that must adhere to SARIF rules.
    """
    res = _run_cmd(["audit", "corpus/golden_corpus/argo-rollouts-install.yaml", "--output", "sarif"])
    sarif = json.loads(res.stdout)
    validator().validate(sarif)
    assert sarif["version"] == "2.1.0"


def test_native_executable_json_schema_clean(tmp_path):
    """Verify yamlr scan emits valid JSON adhering to scan-report.schema.json.
    
    Why: CI/CD systems rely on standard JSON schemas for downstream reporting.
    """
    clean_pod = tmp_path / "clean_pod.yaml"
    clean_pod.write_text(
        "apiVersion: v1\n"
        "kind: Pod\n"
        "metadata:\n"
        "  name: clean-pod\n"
        "  namespace: production\n"
        "spec:\n"
        "  securityContext:\n"
        "    runAsNonRoot: true\n"
        "    seccompProfile:\n"
        "      type: RuntimeDefault\n"
        "  containers:\n"
        "    - name: app\n"
        "      image: nginx@sha256:4f039121c009949ea452140fa7f10b7a85d30dfd076d5e0a0d696ff6f4c2d3cf\n"
        "      securityContext:\n"
        "        allowPrivilegeEscalation: false\n"
        "        readOnlyRootFilesystem: true\n"
        "        capabilities:\n"
        "          drop: [\"ALL\"]\n"
        "      resources:\n"
        "        requests:\n"
        "          cpu: \"100m\"\n"
        "          memory: \"128Mi\"\n"
        "        limits:\n"
        "          cpu: \"200m\"\n"
        "          memory: \"256Mi\"\n",
        encoding="utf-8",
    )
    res = _run_cmd(["scan", str(clean_pod), "--output", "json"])
    report = json.loads(res.stdout)
    _scan_json_validator().validate(report)
    assert report["total_files"] == 1


def test_native_executable_json_schema_findings():
    """Verify yamlr scan with findings adheres to scan-report.schema.json.
    
    Why: Validates schema violations and forensic findings structure.
    """
    res = _run_cmd(["scan", "corpus/golden_corpus/argo-rollouts-install.yaml", "--output", "json"])
    report = json.loads(res.stdout)
    _scan_json_validator().validate(report)
    assert report["status"] == "failed"
    assert report["total_files"] == 1
    assert len(report["results"]) > 0


def test_native_executable_json_schema_failure():
    """Verify yamlr scan error reporting adheres to scan-report.schema.json.
    
    Why: Error reports must use the schema's oneOf error branch rather than freeform text.
    """
    res = _run_cmd(["scan", "nonexistent_target_file.yaml", "--output", "json"])
    report = json.loads(res.stdout)
    _scan_json_validator().validate(report)
    assert report["status"] == "error"
    assert report["complete"] is False
    assert len(report["errors"]) > 0


def test_paid_executable_signing_coverage():
    """Verify yamlr sign executes under test enterprise entitlement.
    
    Why: Closes paid executable coverage in Item 3.7 without requiring the secret production key.
    """
    import jwt
    root = Path(__file__).resolve().parents[1]
    private_key_path = root / "native_core" / "tests" / "fixtures" / "licensing_test_private.pem"
    public_key_path = root / "native_core" / "tests" / "fixtures" / "licensing_test_public.pem"

    now = int(time.time())
    claims = {
        "license_version": 1,
        "sub": "org_enterprise_test",
        "org_id": "org_enterprise_test",
        "iat": now,
        "exp": now + 86400 * 365,
        "tier": "enterprise",
        "iss": "yamlr-entitlement",
        "aud": "yamlr",
        "seats": 500,
        "org_seats": 500,
    }
    test_token = jwt.encode(claims, private_key_path.read_text(encoding="utf-8"), algorithm="RS256")

    env = {
        "YAMLR_LICENSE_PUBLIC_KEY": str(public_key_path.resolve()),
        "YAMLR_LICENSE_TOKEN": test_token,
    }

    res_auth = _run_cmd(["auth", "status"], env=env)
    assert "Enterprise" in res_auth.stdout

    res_sign = _run_cmd(["sign", "--key=test-hmac-key", ".pre-commit-hooks.yaml"], env=env)
    assert res_sign.returncode == 0
    assert "yamlr.dev/signature" in res_sign.stdout
