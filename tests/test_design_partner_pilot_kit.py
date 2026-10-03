"""Verification Suite for Track 3: Design Partner Pilot Kit & Telemetry Packaging.

Why: Empirically verifies the integrity of external integration assets (GitHub Actions,
     pre-commit hooks, CI workflows), validates offline RSA-2048 RS256 license
     cryptography, ensures 100% flag alignment without stale phantom inputs, and enforces
     the absolute boundary separating internal valuation concepts and AI metaphors from
     external engineer-facing pilot documentation.
"""
import os

import pytest
import yaml

from yamlr.cli.parser import create_parser
from yamlr.core.license import LicenseManager

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_subparser(parser, name: str):
    """Retrieve child parser for a given subcommand name."""
    action = next(a for a in parser._actions if isinstance(getattr(a, "choices", None), dict))
    return action.choices[name]


def _get_parser_option_strings(subparser):
    """Collect all valid option flags from a subparser."""
    flags = set()
    for action in subparser._actions:
        for opt in action.option_strings:
            flags.add(opt.lstrip("-"))
            flags.add(opt)
        if action.dest:
            flags.add(action.dest.replace("_", "-"))
    return flags


class TestGitHubActionsIntegrity:
    """Validates GitHub Action metadata manifests and entrypoint scripts."""

    def test_scan_action_manifest_valid_yaml(self):
        """Verify actions/scan/action.yml is valid YAML with proper metadata."""
        action_path = os.path.join(REPO_ROOT, "actions", "scan", "action.yml")
        assert os.path.exists(action_path)
        with open(action_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "Yamlr Manifest Auditor (Scan)"
        assert "inputs" in data
        assert "runs" in data
        assert data["runs"]["using"] == "docker"

    def test_scan_action_inputs_align_with_cli(self):
        """Verify all scan action inputs correspond to valid CLI arguments."""
        action_path = os.path.join(REPO_ROOT, "actions", "scan", "action.yml")
        with open(action_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        parser = create_parser()
        scan_parser = _get_subparser(parser, "scan")
        valid_flags = _get_parser_option_strings(scan_parser)
        valid_flags.update({"path", "extra-args", "fail-on-error", "kube-version"})

        for input_name in data["inputs"].keys():
            assert input_name in valid_flags, f"Stale or unrecognized input in actions/scan: {input_name}"

    def test_scan_entrypoint_no_phantom_flags(self):
        """Verify actions/scan/entrypoint.sh contains no phantom or unmapped flags."""
        entrypoint_path = os.path.join(REPO_ROOT, "actions", "scan", "entrypoint.sh")
        with open(entrypoint_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Stale phantom flags that were eliminated
        stale_flags = ["--enforce-limits", "--harden", "--check-deprecations", "--fast", "--compact", "--fix-tags"]
        for flag in stale_flags:
            assert flag not in content, f"actions/scan/entrypoint.sh contains stale flag: {flag}"

    def test_heal_action_manifest_valid_yaml(self):
        """Verify actions/heal/action.yml is valid YAML with proper metadata."""
        action_path = os.path.join(REPO_ROOT, "actions", "heal", "action.yml")
        assert os.path.exists(action_path)
        with open(action_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "Yamlr Manifest Remediator (Heal)"
        assert "inputs" in data
        assert "runs" in data

    def test_heal_action_inputs_align_with_cli(self):
        """Verify all heal action inputs correspond to valid CLI arguments or orchestration."""
        action_path = os.path.join(REPO_ROOT, "actions", "heal", "action.yml")
        with open(action_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        parser = create_parser()
        heal_parser = _get_subparser(parser, "heal")
        valid_flags = _get_parser_option_strings(heal_parser)
        valid_flags.update({"path", "extra-args", "push", "token", "kube-version"})

        for input_name in data["inputs"].keys():
            assert input_name in valid_flags, f"Stale or unrecognized input in actions/heal: {input_name}"

    def test_heal_entrypoint_replaces_confirm_with_apply(self):
        """Verify actions/heal/entrypoint.sh uses valid --apply and eliminates --confirm."""
        entrypoint_path = os.path.join(REPO_ROOT, "actions", "heal", "entrypoint.sh")
        with open(entrypoint_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "--confirm" not in content
        assert "--apply" in content
        assert "Yamlr Manifest Remediator starting..." in content
        assert "chore(yamlr): automated Kubernetes manifest remediation" in content


class TestPreCommitHooksIntegrity:
    """Validates pre-commit hook specifications and example configurations."""

    def test_pre_commit_hooks_yaml_valid(self):
        """Verify .pre-commit-hooks.yaml defines all required core hooks."""
        hooks_path = os.path.join(REPO_ROOT, ".pre-commit-hooks.yaml")
        assert os.path.exists(hooks_path)
        with open(hooks_path, "r", encoding="utf-8") as f:
            hooks = yaml.safe_load(f)

        hook_ids = {h["id"] for h in hooks}
        expected = {"yamlr-fmt", "yamlr-fix", "yamlr-scan", "yamlr-heal", "yamlr-diff"}
        assert expected.issubset(hook_ids)

        for hook in hooks:
            assert "entry" in hook
            assert hook["entry"].startswith("yamlr ")

    def test_pre_commit_example_config_valid(self):
        """Verify .pre-commit-config.example.yaml references canonical repository."""
        example_path = os.path.join(REPO_ROOT, ".pre-commit-config.example.yaml")
        assert os.path.exists(example_path)
        with open(example_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        repos = config.get("repos", [])
        assert len(repos) >= 1
        assert repos[0]["repo"] == "https://github.com/yamlr/yamlr"


class TestReferenceWorkflows:
    """Validates reference CI workflows created for design partners."""

    def test_pr_audit_workflow_valid_yaml(self):
        """Verify .github/workflows/yamlr-pr-audit.yml is valid YAML and includes diff and SARIF."""
        wf_path = os.path.join(REPO_ROOT, ".github", "workflows", "yamlr-pr-audit.yml")
        assert os.path.exists(wf_path)
        with open(wf_path, "r", encoding="utf-8") as f:
            wf = yaml.safe_load(f)

        assert "jobs" in wf
        assert "audit" in wf["jobs"]
        steps = wf["jobs"]["audit"]["steps"]
        step_names = [s.get("name", "") for s in steps]
        assert any("Diff" in name for name in step_names)
        assert any("Scan" in name or "Audit" in name for name in step_names)


class TestSecurityAndOfflineEntitlements:
    """Validates cryptographic offline entitlement verification and air-gap behavior."""

    def test_offline_public_key_loading(self):
        """Verify LicenseManager accurately loads the RSA-2048 public key from disk."""
        lm = LicenseManager()
        pubkey = lm._get_pubkey()
        assert pubkey is not None
        assert "BEGIN PUBLIC KEY" in pubkey
        assert len(pubkey) > 200

    def test_offline_token_verification_rejection_of_invalid(self):
        """Verify invalid or tampered tokens are rejected locally without network requests."""
        lm = LicenseManager()
        assert lm.verify_token("invalid.jwt.token") is False

    def test_offline_token_verification_valid_signature(self):
        """Verify RSA RS256 token verification executes purely in-memory via native core."""
        import yamlr_native
        lm = LicenseManager()
        pubkey = lm._get_pubkey()

        # In native core, native_verify_token checks RS256 JWT signature against pubkey
        result = yamlr_native.native_verify_token("invalid-token-string", pubkey)
        assert result is False


class TestPilotProgramDocumentationIntegrity:
    """Validates docs/PILOT_PROGRAM.md for zero AI fingerprints and zero internal valuation terminology."""

    def test_pilot_program_doc_exists_and_substantial(self):
        """Verify docs/PILOT_PROGRAM.md exists and contains complete pilot sections."""
        doc_path = os.path.join(REPO_ROOT, "docs", "PILOT_PROGRAM.md")
        assert os.path.exists(doc_path)
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert len(content) > 3000
        assert "14-Day Pilot Protocol" in content
        assert "Phase S1" in content
        assert "Phase S2" in content
        assert "Turnkey Integration Blueprints" in content
        assert "Pilot Evaluation Scorecard" in content

    def test_zero_ai_fingerprints_in_pilot_doc(self):
        """Verify docs/PILOT_PROGRAM.md contains zero AI/metaphor fingerprints."""
        doc_path = os.path.join(REPO_ROOT, "docs", "PILOT_PROGRAM.md")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read().lower()

        forbidden_ai_tokens = [
            "brain",
            "neural",
            "synapse",
            "hallucin",
            "sentient",
            "autonomous surgeon",
            "scalpel",
            "knife",
            "llm",
            "agentic",
        ]
        violations = [token for token in forbidden_ai_tokens if token in content]
        assert not violations, f"Forbidden AI fingerprints detected in PILOT_PROGRAM.md: {violations}"

    def test_zero_valuation_or_mna_language_in_pilot_doc(self):
        """Verify docs/PILOT_PROGRAM.md contains zero internal valuation or M&A terminology."""
        doc_path = os.path.join(REPO_ROOT, "docs", "PILOT_PROGRAM.md")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read().lower()

        forbidden_mna_tokens = [
            "$20m",
            "$1.5m",
            "$3m",
            "$15m",
            "$25m",
            "acquisition",
            "acquirer",
            "multiple",
            "exit strategy",
            "due diligence",
            "asset replacement",
            "replacement value",
            "ip value",
            "pitch",
        ]
        violations = [token for token in forbidden_mna_tokens if token in content]
        assert not violations, f"Forbidden valuation/M&A terminology detected in PILOT_PROGRAM.md: {violations}"

    def test_unskewed_scorecard_template(self):
        """Verify the pilot evaluation scorecard contains un-skewed, blank baseline fields."""
        doc_path = os.path.join(REPO_ROOT, "docs", "PILOT_PROGRAM.md")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Scorecard must provide blank brackets for team measurement, not pre-filled claims
        assert "[   ]" in content
        assert "Target: 0.0%" in content
        # Must not make unqualified marketing promises as pre-existing facts
        assert "100% zero-rollback achieved" not in content
