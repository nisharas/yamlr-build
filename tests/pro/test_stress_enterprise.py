import os
from pathlib import Path

import pytest

from yamlr.core.engine import YamlrEngine

# [QA-12-01] Enterprise Stress Test Suite
# Threshold: 80% Healing Efficiency

FIXTURES_DIR = Path("tests/fixtures")
STRESS_FIXTURE = Path("tests/corpus/stress/benchmark_large.yaml")


@pytest.fixture
def stress_engine():
    engine = YamlrEngine(workspace_path=".")
    yield engine
    engine.close()


def test_gauntlet_healing_efficiency(stress_engine):
    """
    GAUNTLET: Proves Yamlr can heal at least 80% of known broken manifests.

    Why: To ensure enterprise-grade reliability and prevent regressions in
         the core healing engine during complex refactors.
    """
    broken_files = [
        "broken.yaml",
        "test_bad.yaml",
        "test_invalid_configmap.yaml",
        "broken_networkpolicy.yaml",
        "deprecated_resources.yaml",
        "phase9_insecure.yaml",
    ]

    results = []
    for f in broken_files:
        p = FIXTURES_DIR / f
        if p.exists():
            res = stress_engine.audit_and_heal_file(str(p), dry_run=True)
            results.append(res)

    total_files = len(results)
    healed_files = sum(1 for r in results if r.success)

    efficiency = healed_files / total_files if total_files > 0 else 0
    print(f"\n[STRESS] Healing Efficiency: {efficiency:.2%} ({healed_files}/{total_files})")

    assert efficiency >= 0.8, f"Healing Efficiency {efficiency:.2%} is below the 80% enterprise threshold!"


def test_large_manifest_stress(stress_engine):
    """
    STRESS: Processes a 2MB+ manifest to verify engine stability.
    """
    if not STRESS_FIXTURE.exists():
        pytest.skip("Stress fixture benchmark_large.yaml not found.")

    res = stress_engine.audit_and_heal_file(str(STRESS_FIXTURE), dry_run=True)
    assert res.success, f"Failed to process large manifest: {res.error}"
    assert res.processing_time_seconds < 10.0, "Large manifest processing took too long (>10s)"


def test_crash_detection_automation(stress_engine):
    """
    [QA-12-05] CRASH DETECTION: Verifies CLI reports exit code 2 on internal failure.

    Why: To ensure CI pipelines fail appropriately when the engine crashes,
         preventing "silent failures" in automated environments.
    """
    from unittest.mock import MagicMock, patch

    from yamlr.models import HealFileResult

    # We mock batch_heal to simulate an ENGINE_ERROR result
    with patch.object(YamlrEngine, "batch_heal") as mock_batch:
        mock_batch.return_value = [
            HealFileResult(
                file_path="crash.yaml",
                full_path="crash.yaml",
                success=False,
                status="ENGINE_ERROR",
                kind="Unknown",
                logic_logs=["CRITICAL: Simulation"],
                findings=[],
                dna_integrity_score=0,
                identities=[],
                error="Simulated Engine Crash",
            )
        ]

        # Simulate the CLI entrypoint check (what [QA-12-05] is about)
        from yamlr.core.entrypoints.scan import handle_scan_command

        args = MagicMock()
        args.path = [str(FIXTURES_DIR)]
        args.output = "text"
        args.identity_mode = "infer"
        args.enforce_limits = False
        args.fix_tags = False
        args.harden = False
        args.enforce_probes = False
        args.strict = False
        args.compact = False
        args.fast = False
        args.check_deprecations = False
        args.extensions = [".yaml", ".yml"]
        args.max_depth = 1
        args.scout = False
        args.use_rust = False
        args.stream_to = None
        args.verbose = False
        args.summary_only = False

        formatter = MagicMock()

        # handle_scan_command should return 2 directly based on our changes in scan.py
        exit_code = handle_scan_command(args, stress_engine)
        assert exit_code == 2, f"Expected exit code 2 on ENGINE_ERROR, got {exit_code}"
