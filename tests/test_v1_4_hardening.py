import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def run_yamlr(args, env_override=None):
    """Helper to run yamlr CLI with PYTHONPATH set."""
    # Ensure src is in PYTHONPATH
    src_dir = str(Path(__file__).parent.parent / "src")

    cmd = [os.sys.executable, "-m", "yamlr.cli.main"] + args
    env = os.environ.copy()
    env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")

    if env_override:
        env.update(env_override)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8")

    if result.returncode != 0 and "-h" not in args:
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

    return result


def test_v1_4_help_filtration():
    """Verify that non-CORE commands are suppressed from default help."""
    # 1. Default Help
    result = run_yamlr(["-h"])
    assert result.returncode == 0
    # Core should be there
    assert "scan" in result.stdout
    assert "heal" in result.stdout
    assert "doctor" in result.stdout

    # Insight/Pipeline should be SUPPRESSED
    assert "idp-export" not in result.stdout
    assert "graph" not in result.stdout
    assert "pulse" not in result.stdout
    assert "dna" not in result.stdout


def test_v1_4_all_help_visibility():
    """Verify that --all reveals suppressed commands."""
    result = run_yamlr(["--all", "-h"])
    assert result.returncode == 0
    # Now they should be visible
    assert "idp-export" in result.stdout
    assert "graph" in result.stdout
    assert "pulse" in result.stdout
    assert "dna" in result.stdout


def test_v1_4_doctor_execution():
    """Verify the doctor command runs and produces a compact table."""
    result = run_yamlr(["doctor"])
    assert result.returncode == 0
    assert "Yamlr Doctor" in result.stdout
    assert "Runtime" in result.stdout
    assert "License" in result.stdout
    assert "PASS" in result.stdout or "FREE" in result.stdout


def test_v1_4_capability_shield_logic():
    """Unit test for CapabilityShield policies."""
    from yamlr.core.bridge import YamlrBridge

    caps = YamlrBridge.capabilities

    # Mock Pro status
    with patch("yamlr.core.bridge.YamlrBridge.is_pro_enabled", return_value=False):
        assert caps.can_harden_security() is False
        assert caps.can_export_format("sarif") is False
        assert caps.can_export_format("json") is True
        assert caps.get_healing_limit() == 5

    with patch("yamlr.core.bridge.YamlrBridge.is_pro_enabled", return_value=True):
        assert caps.can_harden_security() is True
        assert caps.can_export_format("sarif") is True
        assert caps.get_healing_limit() > 100


def test_v1_4_idp_export_init():
    """Verify idp-export init generates a template."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "backstage.yaml"
        result = run_yamlr(["idp-export", "init", "--format", "backstage", "--output", str(out_file)])
        assert result.returncode == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "Yamlr Backstage Integration Template" in content
        assert "yamlr.io/safety-score" in content
        assert "yamlr.io/dna-integrity" in content


def test_v1_4_granular_pro_gating():
    """Verify that high-risk flags are intercepted in Free mode."""
    # 1. Test --sovereign in scan (Free)
    result = run_yamlr(["scan", ".", "--sovereign"])
    # Should contain the Pro required notification
    assert "Yamlr Pro Required" in result.stdout
    assert "Sovereign Sorting" in result.stdout

    # 2. Test --harden in heal (Free)
    # We use a dummy file to avoid real healing
    result = run_yamlr(["heal", "nonexistent.yaml", "--harden"])
    assert "Yamlr Pro Required" in result.stdout
    assert "Security Hardening" in result.stdout

    # 3. Test --enforce-limits in scan (Free)
    result = run_yamlr(["scan", ".", "--enforce-limits"])
    assert "Yamlr Pro Required" in result.stdout
    assert "Resource Limit Enforcement" in result.stdout


def test_v1_4_modular_detectors_parity():
    """Verify that refactored detectors still work correctly."""
    from yamlr.analyzers.detectors.config import detect_broken_refs
    from yamlr.analyzers.detectors.traffic import detect_ghost_services
    from yamlr.models import ManifestIdentity

    # Simple Ghost Service Test
    svc = ManifestIdentity(kind="Service", name="ghost", selector={"app": "missing"})
    workload = ManifestIdentity(kind="Deployment", name="app", labels={"app": "wrong"})

    ghosts = detect_ghost_services([svc], [workload])
    assert len(ghosts) == 1
    assert ghosts[0]["name"] == "ghost"
    assert "Add a Deployment with matching labels" in ghosts[0]["hint"]

    # Simple Broken Ref Test
    w = ManifestIdentity(kind="Deployment", name="web", config_refs=["missing-cm"])
    broken = detect_broken_refs([w], index={})
    assert len(broken) == 1
    assert broken[0]["name"] == "missing-cm"
    assert "ConfigMap" in broken[0]["kind"]
