"""Safety checks for Yamlr's automated manifest commits."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _find_bash():
    candidates = [shutil.which("bash")]
    if os.name == "nt":
        candidates.extend(
            [
                r"C:\Program Files\Git\bin\bash.exe",
                r"C:\Program Files\Git\usr\bin\bash.exe",
            ]
        )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            probe = subprocess.run(
                [candidate, "--version"], capture_output=True, text=True, check=False
            )
            if probe.returncode == 0:
                return candidate
    return None


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def test_staging_helper_stages_only_changed_yaml_under_target(tmp_path):
    bash = _find_bash()
    if not bash:
        pytest.skip("Bash is required to exercise the manifest staging helper.")

    repo = tmp_path / "repo"
    target = repo / "manifests"
    outside = repo / "outside"
    target.mkdir(parents=True)
    outside.mkdir()
    (target / "deployment.yaml").write_text("spec: old\n", encoding="utf-8")
    (target / "removed.yaml").write_text("kind: old\n", encoding="utf-8")
    (outside / "unrelated.yaml").write_text("kind: old\n", encoding="utf-8")
    (repo / "README.txt").write_text("old\n", encoding="utf-8")

    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.name", "Yamlr Test")
    _git(repo, "config", "user.email", "yamlr-test@example.invalid")
    _git(repo, "add", "--all")
    _git(repo, "commit", "--quiet", "-m", "initial")

    (target / "deployment.yaml").write_text("spec: healed\n", encoding="utf-8")
    (target / "new manifest.yml").write_text("kind: new\n", encoding="utf-8")
    (target / "removed.yaml").unlink()
    (outside / "unrelated.yaml").write_text("kind: changed\n", encoding="utf-8")
    (repo / "README.txt").write_text("changed\n", encoding="utf-8")

    helper = REPO_ROOT / "actions" / "stage_manifest_changes.sh"
    subprocess.run(
        [bash, str(helper), "manifests"], cwd=repo, check=True, capture_output=True
    )

    staged = _git(repo, "diff", "--cached", "--name-only").stdout.splitlines()
    assert staged == ["manifests/deployment.yaml", "manifests/new manifest.yml"]
    assert _git(repo, "diff", "--cached", "--name-status").stdout.count("D\t") == 0
    unstaged = _git(repo, "status", "--porcelain").stdout
    assert "outside/unrelated.yaml" in unstaged
    assert "README.txt" in unstaged


def test_heal_autocommit_paths_validate_and_limit_staging():
    root_action = yaml.safe_load((REPO_ROOT / "action.yml").read_text(encoding="utf-8"))
    steps = root_action["runs"]["steps"]
    preflight = next(step for step in steps if step.get("name") == "Validate Workspace Before Autocommit")
    commit_step = next(step for step in steps if step.get("name") == "Commit and Push Manifest Changes")

    assert preflight["if"] == "inputs.autocommit == 'true'"
    assert "git status --porcelain=v1 --untracked-files=all" in preflight["run"]
    assert "actions/stage_manifest_changes.sh" in commit_step["run"]
    assert "git add -A" not in commit_step["run"]

    entrypoint = (REPO_ROOT / "actions" / "heal" / "entrypoint.sh").read_text(
        encoding="utf-8"
    )
    assert 'if [ "$PUSH" = "true" ] && [ -n "$(git status --porcelain=v1 --untracked-files=all)" ]; then' in entrypoint
    assert entrypoint.index("Refusing automatic commit") < entrypoint.index('"${CMD_ARRAY[@]}"')
    assert "/stage_manifest_changes.sh \"$TARGET_PATH\"" in entrypoint
    assert "git add ." not in entrypoint
    assert 'if [ "$PUSH" = "true" ]; then' in entrypoint


def test_docker_heal_action_defaults_to_preview_and_requires_apply_before_push():
    action = yaml.safe_load(
        (REPO_ROOT / "actions" / "heal" / "action.yml").read_text(encoding="utf-8")
    )
    assert action["inputs"]["apply"]["default"] == "false"

    entrypoint = (REPO_ROOT / "actions" / "heal" / "entrypoint.sh").read_text(
        encoding="utf-8"
    )
    assert "APPLY=${INPUT_APPLY:-false}" in entrypoint
    assert 'if [ "$PUSH" = "true" ] && [ "$APPLY" != "true" ]; then' in entrypoint
    assert 'if [ "$APPLY" = "true" ]; then' in entrypoint


def test_composite_heal_action_does_not_force_apply_for_preview():
    action = yaml.safe_load((REPO_ROOT / "action.yml").read_text(encoding="utf-8"))
    execute = next(
        step for step in action["runs"]["steps"] if step.get("name") == "Execute Yamlr Engine"
    )
    run_script = execute["run"]
    assert 'COMMAND+=(heal "$YAMLR_PATH")' in run_script
    assert 'COMMAND+=(--apply)' in run_script
    assert 'COMMAND+=(heal "$YAMLR_PATH" --apply)' not in run_script
