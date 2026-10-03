from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

def test_precommit_hooks_yaml_validity():
    """Verify that .pre-commit-hooks.yaml exists, parses, and defines required hooks."""
    hooks_file = ROOT / ".pre-commit-hooks.yaml"
    assert hooks_file.exists(), ".pre-commit-hooks.yaml must exist at repo root"
    
    with open(hooks_file, "r", encoding="utf-8") as f:
        hooks = yaml.safe_load(f)
    
    assert isinstance(hooks, list), ".pre-commit-hooks.yaml must be a list of hook definitions"
    hook_ids = {h.get("id"): h for h in hooks}
    
    # 1. Verify yamlr-fmt
    assert "yamlr-fmt" in hook_ids, "yamlr-fmt hook must be defined"
    fmt = hook_ids["yamlr-fmt"]
    assert "yamlr fmt" in fmt.get("entry", "")
    assert "-w" in fmt.get("args", [])
    assert fmt.get("pass_filenames") is True
    
    # 2. Verify yamlr-fix
    assert "yamlr-fix" in hook_ids, "yamlr-fix hook must be defined"
    fix = hook_ids["yamlr-fix"]
    assert "yamlr fix" in fix.get("entry", "")
    assert fix.get("pass_filenames") is True

    # 3. Verify backward-compatible yamlr-scan and yamlr-heal
    assert "yamlr-scan" in hook_ids, "yamlr-scan hook must be preserved"
    assert "yamlr-heal" in hook_ids, "yamlr-heal hook must be preserved"

def test_precommit_config_example_validity():
    """Verify that .pre-commit-config.example.yaml parses cleanly."""
    example_file = ROOT / ".pre-commit-config.example.yaml"
    assert example_file.exists(), ".pre-commit-config.example.yaml must exist"
    
    with open(example_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    assert "repos" in config
    assert len(config["repos"]) > 0
    repo = config["repos"][0]
    hook_ids = [h["id"] for h in repo.get("hooks", [])]
    assert "yamlr-fmt" in hook_ids
    assert "yamlr-fix" in hook_ids

def test_github_action_yaml_validity():
    """Verify that action.yml parses and exposes all GitOps inputs."""
    action_file = ROOT / "action.yml"
    assert action_file.exists(), "action.yml must exist at repo root"
    
    with open(action_file, "r", encoding="utf-8") as f:
        action = yaml.safe_load(f)
    
    inputs = action.get("inputs", {})
    assert "command" in inputs
    assert "write" in inputs
    assert "check" in inputs
    assert "autocommit" in inputs
    assert "commit-message" in inputs
    assert "path" in inputs

def test_github_workflow_gitops_yaml_validity():
    """Verify that .github/workflows/yamlr-gitops.yml is valid YAML."""
    wf_file = ROOT / ".github" / "workflows" / "yamlr-gitops.yml"
    assert wf_file.exists(), "yamlr-gitops.yml workflow must exist"
    
    with open(wf_file, "r", encoding="utf-8") as f:
        wf = yaml.safe_load(f)
    
    assert "on" in wf or True in wf, "Workflow must define trigger events"
    assert "jobs" in wf
    assert "gitops-fmt-and-fix" in wf["jobs"]
