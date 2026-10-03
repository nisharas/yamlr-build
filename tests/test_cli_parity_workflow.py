"""Keep the Python/Rust command-line parity suite in the release CI path."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_workflow(name: str) -> dict:
    return yaml.load(
        (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def test_ci_builds_both_frontends_and_runs_the_shared_contract_matrix():
    workflow = load_workflow("ci.yml")
    job = workflow["jobs"]["python-rust-cli-parity"]
    commands = [step.get("run", "") for step in job["steps"]]

    assert any("cargo build --locked" in command for command in commands)
    assert any("python tests/verify_rust_parity.py" in command for command in commands)
    assert any('--editable ".[dev]"' in command for command in commands)
    assert any(
        "python scripts/ci/verify_report_contracts.py" in command
        for command in commands
    )


def test_release_workflows_require_ci_parity_gate():
    for filename, build_job in (
        ("release.yml", "build"),
        ("release-binaries.yml", "build-release"),
    ):
        workflow = load_workflow(filename)
        assert workflow["jobs"]["validate"]["uses"] == "./.github/workflows/ci.yml"
        assert "validate" in workflow["jobs"][build_job]["needs"]


def test_clean_wheel_job_runs_installed_extension_parity_on_each_host():
    job = load_workflow("ci.yml")["jobs"]["python-wheel-smoke"]
    assert set(job["strategy"]["matrix"]["os"]) == {
        "ubuntu-latest",
        "macos-latest",
        "macos-15-intel",
        "windows-latest",
    }
    commands = [step.get("run", "") for step in job["steps"]]
    build_index = next(
        i for i, command in enumerate(commands) if "cargo build --locked" in command
    )
    parity_index = next(
        i
        for i, command in enumerate(commands)
        if "smoke_wheel.py wheel-dist --native-bin" in command
    )
    assert build_index < parity_index


def test_action_verification_does_not_call_the_removed_stub_parity_guard():
    workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "verify_actions.yml"
    ).read_text(encoding="utf-8")
    assert "tests/stubs/rust_scanner_stub.py" not in workflow_text


def test_release_uses_an_explicit_supported_intel_host_and_unique_artifacts():
    binaries = load_workflow("release-binaries.yml")["jobs"]["build-release"]
    intel = next(
        row
        for row in binaries["strategy"]["matrix"]["include"]
        if row["target"] == "x86_64-apple-darwin"
    )
    assert intel["os"] == "macos-15-intel"
    release = load_workflow("release.yml")["jobs"]["build"]
    assert "macos-15-intel" in release["strategy"]["matrix"]["os"]
    uploads = [
        step
        for step in release["steps"]
        if step.get("uses", "").startswith("actions/upload-artifact@")
    ]
    assert all("runner.arch" in step["with"]["name"] for step in uploads)
    assert any(
        "smoke_wheel.py dist --native-bin" in step.get("run", "")
        for step in release["steps"]
    )
