from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from yamlr.core.bridge import YamlrBridge
from yamlr.core.entrypoints.display import print_version


def test_machine_id_stability():
    """Verify that machine ID is stable across calls but unique-ish."""
    id1 = YamlrBridge.get_machine_id()
    id2 = YamlrBridge.get_machine_id()
    assert id1 == id2
    assert len(id1) == 12


def test_checkout_url_attribution():
    """Verify that checkout URL contains the machine ID."""
    url = YamlrBridge.get_checkout_url()
    machine_id = YamlrBridge.get_machine_id()
    assert machine_id in url
    assert "utm_source=yamlr_cli" in url
    assert "utm_medium=version_tip" in url


@patch("yamlr.core.entrypoints.display.get_console")
def test_version_output_conversion_hint(mock_get_console):
    """Verify that the version command displays the conversion hint for non-pro users."""
    console = Console(file=StringIO(), force_terminal=False, color_system=None)
    mock_get_console.return_value = console

    with patch("yamlr.core.bridge.YamlrBridge.is_pro_enabled", return_value=False):
        with patch("yamlr.core.bridge.YamlrBridge.get_checkout_url", return_value="https://yamlr.dev/test-attr"):
            print_version("yamlr", is_pro=False)
            output = console.file.getvalue()
            # De-emoji the check for stability
            assert "Unlock high-gravity healing" in output
            assert "https://yamlr.dev/test-attr" in output


def test_pro_preview_flag_propagation():
    """Verify that the --pro-preview flag is correctly parsed and passed."""
    from yamlr.cli.parser_factory import create_parser

    parser = create_parser("yamlr")

    # Test scan command
    args = parser.parse_args(["scan", ".", "--pro-preview"])
    assert args.pro_preview is True

    # Test heal command
    args = parser.parse_args(["heal", "test.yaml", "--pro-preview"])
    assert args.pro_preview is True


@patch("yamlr.core.bridge.YamlrBridge.is_pro_enabled", return_value=False)
@patch("yamlr.core.entrypoints.upgrade.YamlrBridge.is_pro_enabled", return_value=False)
@patch("yamlr.core.entrypoints.upgrade.get_checkout_url", return_value="https://yamlr.dev/pro")
def test_upgrade_dashboard_rendering(mock_checkout, mock_pro_inner, mock_pro_outer):
    """Verify that the upgrade command renders the feature matrix."""
    from yamlr.core.entrypoints.upgrade import handle_upgrade_command

    console = Console(file=StringIO(), force_terminal=False, color_system=None)
    args = MagicMock()
    engine = MagicMock()

    handle_upgrade_command(args, engine, console)
    output = console.file.getvalue()

    assert "SURGICAL TIER COMPARISON" in output
    assert "Signed DNA Performance Receipts" in output
    assert "https://yamlr.dev/pro" in output
    assert "PRO UPGRADE HINT" in output


def test_pro_preview_dopamine_drip():
    """Verify that simulated Pro fixes trigger the conversion UI (Dopamine Drip)."""
    import io
    from unittest.mock import MagicMock

    from rich.console import Console

    from yamlr.core.advisory import AdvisoryData, AdvisoryRenderer
    from yamlr.core.entrypoints.base import set_console
    from yamlr.models import HealAction, HealFileResult

    console_out = io.StringIO()
    test_console = Console(file=console_out, force_terminal=False, color_system=None, width=100)
    set_console(test_console)
    renderer = AdvisoryRenderer(test_console)

    # Mock a result with Pro fixes triggered
    mock_result = MagicMock(spec=HealFileResult)
    mock_result.file_path = "deployment.yaml"
    mock_result.status = "PREVIEW"
    mock_result.pro_features_triggered = True
    mock_result.raw_content = "kind: Deployment\nmetadata:\n  name: nginx"
    mock_result.healed_content = (
        'kind: Deployment\nmetadata:\n  name: nginx\n  annotations:\n    yamlr.dev/harden: "true"'
    )

    # [QA-12-FIX] Ensure numeric comparisons in UI don't trigger TypeErrors on Mocks
    mock_result.dna_integrity_score = 100
    mock_result.trust_score = 95.0
    mock_result.phy_status = "100%"
    mock_result.kbs_status = "100%"
    mock_result.sem_status = "100%"
    mock_result.get.side_effect = lambda k, d=None: getattr(mock_result, k, d)

    # Findings must be list of objects or dicts
    mock_result.findings = [
        {
            "analyzer": "cross-resource",
            "severity": "info",
            "message": "Pro Fix Simulated",
            "rule_id": "rule/ghost-service",
        }
    ]
    # [QA-12-FIX] Ensure numeric properties are real values
    mock_result.processing_stats = {
        "lexer_repairs": 0,
        "lexer_typos": 0,
        "semantic_repairs": 0,
        "security_hardens": 0,
        "migrator_changes": 0,
    }
    mock_result.identities = [{"kind": "Deployment", "name": "nginx"}]

    data = AdvisoryData(results=[mock_result], pro_preview=True, is_dry_run=True)

    # 1. Test render_scan_report triggers pro_preview
    args = MagicMock()
    args.diff = False
    args.verbose = False
    mock_engine = MagicMock()
    mock_engine.is_pro_enabled.return_value = False
    mock_engine.cluster_version = "v1.31"
    mock_engine.telemetry.get_stats.return_value = {"last_dna_integrity_score": 85.0, "surgical_efficiency": 1.2}
    renderer.render_scan_report(data, mock_engine, args)

    output = console_out.getvalue()
    print(f"DEBUG OUTPUT:\n{output}")
    assert "Yamlr Pro Preview Active" in output
    assert "Proposed Pro Repairs" in output
    assert "Cross-Resource Auto-Repair" in output
    assert "deployment.yaml" in output

    # 2. Test render_heal_results triggers Pro CTA
    console_out.truncate(0)
    console_out.seek(0)
    renderer.render_heal_results(data, mock_engine)
    output = console_out.getvalue()
    print(f"DEBUG OUTPUT CTA:\n{output}")
    assert "Unlock Yamlr Enterprise" in output
    assert "https://yamlr.dev/pro" in output
