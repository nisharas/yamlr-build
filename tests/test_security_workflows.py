"""Regression tests for security workflow enforcement."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_workflows_require_the_security_audit_gate():
    for filename, build_job in (
        ("release.yml", "build"),
        ("release-binaries.yml", "build-release"),
    ):
        workflow = yaml.load(
            (REPO_ROOT / ".github" / "workflows" / filename).read_text(
                encoding="utf-8"
            ),
            Loader=yaml.BaseLoader,
        )

        assert workflow["jobs"]["security-audit"]["uses"] == (
            "./.github/workflows/security_audit.yml"
        )
        assert "security-audit" in workflow["jobs"][build_job]["needs"]

    security = yaml.load(
        (REPO_ROOT / ".github" / "workflows" / "security_audit.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    commands = [step.get("run", "") for job in security["jobs"].values() for step in job["steps"]]
    assert any("cargo audit" in command for command in commands)
    assert any("pip-audit --strict" in command for command in commands)
    assert any("detect-secrets-hook --baseline .secrets.baseline" in command for command in commands)


def test_release_workflows_publish_sboms_and_dependency_license_notices():
    ci = yaml.load(
        (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    javascript_policy = ci["jobs"]["javascript-license-policy"]
    package_step = next(
        step
        for step in javascript_policy["steps"]
        if step.get("name") == "Package JavaScript license inventory and notices"
    )
    upload_step = next(
        step
        for step in javascript_policy["steps"]
        if step.get("name") == "Upload JavaScript license inventory and notices"
    )
    assert "zip -qr" in package_step["run"]
    assert "yamlr-third-party-js-${{ matrix.workspace }}.zip" in upload_step["with"]["path"]

    releases = {
        "release.yml": "dist/yamlr-sbom-${{ runner.os }}-${{ runner.arch }}.cdx.json",
        "release-binaries.yml": "yamlr-sbom-${{ matrix.target }}.cdx.json",
    }
    for filename, sbom_name in releases.items():
        workflow = yaml.load(
            (REPO_ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )
        sbom_steps = [
            step
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if step.get("uses", "").startswith("anchore/sbom-action@")
        ]
        assert sbom_steps, f"{filename} must generate a release SBOM"
        assert any(step["with"].get("output-file") == sbom_name for step in sbom_steps)
        assert any(
            "yamlr-sbom-*.cdx.json" in step.get("with", {}).get("subject-path", "")
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
        )
        assert any(
            "yamlr-third-party-js-${workspace}.zip" in step.get("run", "")
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
        )


def test_dependency_audit_workflows_fail_on_vulnerability_findings():
    workflow_paths = (
        REPO_ROOT / ".github" / "workflows" / "security.yml",
        REPO_ROOT / ".github" / "workflows" / "security_scan.yml",
        REPO_ROOT / ".github" / "workflows" / "security_audit.yml",
    )

    for workflow_path in workflow_paths:
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        audit_steps = [
            step
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if "pip-audit" in step.get("run", "")
        ]

        assert audit_steps, f"{workflow_path.name} must run pip-audit"
        for step in audit_steps:
            command = step["run"]
            assert "|| true" not in command, workflow_path.name
            assert "continue-on-error" not in step, workflow_path.name


def test_secret_scan_workflows_require_and_compare_a_committed_baseline():
    workflow_paths = (
        REPO_ROOT / ".github" / "workflows" / "security_audit.yml",
        REPO_ROOT / ".github" / "workflows" / "security_scan.yml",
    )

    for workflow_path in workflow_paths:
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        steps = next(iter(workflow["jobs"].values()))["steps"]
        baseline_gate = next(
            step for step in steps if step.get("name") == "Require reviewed secret baseline"
        )
        secret_scan = next(
            step
            for step in steps
            if "detect-secrets-hook" in step.get("run", "")
        )

        assert "[ ! -s .secrets.baseline ]" in baseline_gate["run"]
        assert "json.loads" in baseline_gate["run"]
        assert "--baseline .secrets.baseline" in secret_scan["run"]
        assert "detect-secrets scan" not in secret_scan["run"]
        assert "> .secrets.baseline" not in secret_scan["run"]
        assert "set -o pipefail" in secret_scan["run"]
        assert "grep -zEv" in secret_scan["run"]


def test_gitops_write_token_is_never_exposed_to_pull_request_code():
    workflow_path = REPO_ROOT / ".github" / "workflows" / "yamlr-gitops.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert "pull_request" not in workflow["on"]
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["gitops-fmt-and-fix"]
    assert job["permissions"] == {"contents": "write"}
    assert "pull-requests" not in job["permissions"]
    assert "github.event_name != 'workflow_dispatch'" in job["if"]
    assert "refs/heads/main" in job["if"]
    assert "refs/heads/master" in job["if"]


def test_dogfood_write_permissions_are_absent_from_pull_request_runs():
    workflow_path = REPO_ROOT / ".github" / "workflows" / "dogfood.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert "pull_request" not in workflow["on"]
    assert workflow["permissions"] == {"contents": "read"}
    action_job = workflow["jobs"]["action-check"]
    assert action_job["permissions"] == {"contents": "read"}
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert not any(
        step.get("uses", "").startswith("github/codeql-action/upload-sarif@")
        for step in action_job["steps"]
    )
    action = next(step for step in action_job["steps"] if step.get("name") == "Dogfood Yamlr Action")
    assert action["with"]["command"] == "scan"
    assert action["with"]["version"] == "v0.1.0"
    assert action["with"]["allow-local-fallback"] == "true"


def test_safety_scan_keeps_security_events_write_permission_out_of_untrusted_scan_job():
    workflow_path = REPO_ROOT / ".github" / "workflows" / "yamlr-safety.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert workflow["permissions"] == {"contents": "read"}
    audit = workflow["jobs"]["audit"]
    assert "permissions" not in audit
    assert any("upload-artifact@" in step.get("uses", "") for step in audit["steps"])

    publisher = workflow["jobs"]["publish-sarif"]
    assert publisher["needs"] == "audit"
    assert publisher["permissions"] == {
        "contents": "read",
        "security-events": "write",
    }
    assert "github.event.pull_request.head.repo.full_name == github.repository" in publisher["if"]
    assert any("upload-sarif@" in step.get("uses", "") for step in publisher["steps"])


def test_pr_audit_limits_security_events_write_to_same_repo_sarif_publisher():
    workflow_path = REPO_ROOT / ".github" / "workflows" / "yamlr-pr-audit.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert workflow["permissions"] == {"contents": "read"}
    audit = workflow["jobs"]["audit"]
    assert "permissions" not in audit
    assert any("upload-artifact@" in step.get("uses", "") for step in audit["steps"])

    publisher = workflow["jobs"]["publish-sarif"]
    assert publisher["needs"] == "audit"
    assert publisher["permissions"] == {
        "contents": "read",
        "security-events": "write",
    }
    assert "github.event.pull_request.head.repo.full_name == github.repository" in publisher["if"]
    assert any("upload-sarif@" in step.get("uses", "") for step in publisher["steps"])
