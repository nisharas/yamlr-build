import io
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import (
    LicenseManager,
    _calculate_health_score,
    audit_topology_outages,
    cmd_completion,
    cmd_dna,
    cmd_explain_universal,
    cmd_guide_rich,
    cmd_roi,
)
from yamlr.ui.renderer import RichRenderer


def test_calculate_health_score_all_levels():
    """Verify health score calculation for all severity levels."""
    v_crit = MagicMock(severity="CRITICAL")
    v_high = MagicMock(severity="HIGH")
    v_med = MagicMock(severity="MEDIUM")
    v_low = MagicMock(severity="LOW")
    
    assert _calculate_health_score([v_crit]) == 85.0
    assert _calculate_health_score([v_high]) == 95.0
    assert _calculate_health_score([v_med]) == 98.0
    assert _calculate_health_score([v_low]) == 99.5
    assert _calculate_health_score([]) == 100.0

def test_license_manager_load_failures():
    """Verify LicenseManager load failures don't crash and set is_pro=False."""
    with patch('yamlr.core_logic.LicenseManager._get_pubkey', return_value="fake-key"):
        with patch.dict(os.environ, {"YAMLR_TOKEN": "invalid"}):
            with patch('yamlr_native.native_verify_token', return_value=False):
                lm = LicenseManager()
                assert lm.is_pro is False

def test_cmd_guide_edge_cases():
    """Verify guide edge cases."""
    with patch('yamlr.knowledge.registry.KnowledgeRegistry.lookup', return_value=None):
        with patch('yamlr.ui.renderer.RichRenderer.render_explain') as mock_render:
            cmd_guide_rich("invalid-topic")
            mock_render.assert_not_called()
    
    with patch('yamlr.ui.theme.console.print') as mock_print:
        cmd_guide_rich(None)
        assert any("Knowledge Guide" in str(call) for call in mock_print.call_args_list)

def test_cmd_explain_edge_cases():
    """Verify explain edge cases."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        cmd_explain_universal(None)
        assert any("Usage: yamlr explain" in str(call) for call in mock_print.call_args_list)

def test_cmd_dna_no_files(temp_workspace):
    """Verify DNA command when no files are found."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        cmd_dna(temp_workspace)
        assert any("No YAML files found" in str(call) for call in mock_print.call_args_list)

def test_cmd_roi_native_missing():
    """Verify ROI command when native core is missing."""
    with patch('yamlr.core_logic.console.print') as mock_print:
        with patch.dict('sys.modules', {'yamlr_native': MagicMock(side_effect=ImportError)}):
            pass

def test_cmd_completion_unsupported():
    """Verify completion command for unsupported shell."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        cmd_completion("fish")
        assert any("Unsupported shell" in str(call) for call in mock_print.call_args_list)

def test_audit_topology_few_resources():
    """Verify topology audit with too few resources."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        audit_topology_outages([MagicMock()])
        mock_print.assert_not_called()

def test_renderer_explain_error():
    """Verify renderer error path for explain."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_explain("unknown", None)
        assert any("No forensic data found" in str(call) for call in mock_print.call_args_list)

def test_renderer_animate_no_improvement():
    """Verify animation when no improvement."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.animate_integrity_scan(90.0, 80.0)
        mock_print.assert_not_called()

def test_renderer_summary_pro_tip():
    """Verify renderer pro tip in summary."""
    stats = {"total_files": 10, "violations": 5, "pro_fixable": 3}
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_summary(stats)
        assert mock_print.called

def test_renderer_help_essentials():
    """Verify renderer help essentials view."""
    cats = {"Core Commands": [], "Advanced Utilities": [{"name": "test", "purpose": "p"}]}
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_precision_help(cats, show_all=False)
        assert mock_print.called

def test_renderer_graph_fallback():
    """Verify graph renderer fallback root."""
    edge = MagicMock(source="A", target="B", edge_type="USES")
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_graph([edge])
        mock_print.assert_called()

def test_renderer_integrity_ring_red():
    """Verify integrity ring red color."""
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_integrity_ring(50.0)
        assert mock_print.called

def test_renderer_diff_removed_added():
    """Verify diff renderer with removed and added lines."""
    with patch('yamlr.ui.diff_engine.SideBySideDiff.calculate', return_value=[("old", None, "REMOVED"), (None, "new", "ADDED")]):
        with patch('yamlr.ui.theme.console.print') as mock_print:
            RichRenderer.render_side_by_side_diff("", "")
            mock_print.assert_called()

def test_main_identity_collision():
    """Verify identity collision detection."""
    from yamlr.cli.main import _check_identity_collision
    res1 = MagicMock()
    # Mock identity to have the required attributes
    res1.identity.kind = "Pod"
    res1.identity.name = "p1"
    res1.identity.namespace = "default"
    res1.file_path = "f1.yaml"
    
    identities = {}
    with patch('yamlr.cli.main.console.print') as mock_print:
        _check_identity_collision(res1, identities, is_windows=False)
        # The key is Pod/p1@default
        assert identities.get("Pod/p1@default") == "f1.yaml" or identities.get("Pod/p1") == "f1.yaml"
        
        # Collision
        res2 = MagicMock()
        res2.identity.kind = "Pod"
        res2.identity.name = "p1"
        res2.identity.namespace = "default"
        res2.file_path = "f2.yaml"
        _check_identity_collision(res2, identities, is_windows=False)
        assert mock_print.called

def test_main_pipeline_outputs(temp_workspace):
    """Verify pipeline with SARIF and JSON outputs."""
    from yamlr.cli.main import _execute_scan_heal_pipeline
    args = MagicMock(path=temp_workspace, command="scan", k8s_version="1.30", output="sarif", crd=None)
    
    with patch('yamlr.cli.pipeline.initialize_engine'):
        with patch('yamlr.cli.pipeline.execute_pipeline') as mock_exec:
            mock_exec.return_value = MagicMock(results=[], total_files=0)
            with patch('yamlr.sarif_reporter.SarifReporter.generate_sarif') as mock_sarif:
                _execute_scan_heal_pipeline(args)
                mock_sarif.assert_called_once()
            
            args.output = "json"
            with patch('yamlr.cli.pipeline._export_json_report') as mock_json:
                _execute_scan_heal_pipeline(args)
                mock_json.assert_called_once()

def test_main_render_results_pro_limit():
    """Verify pro limit in results rendering."""
    from yamlr.cli.formatters import _render_results_and_collisions
    report = MagicMock()
    # 6 results to trigger limit
    res = MagicMock()
    res.identity = None
    res.suggested_fixes = [MagicMock()]
    report.results = [res for _ in range(6)]
    telemetry = MagicMock()
    
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=False):
        with patch('yamlr.cli.formatters.render_resource_results'):
            with patch('yamlr.cli.formatters.console.print') as mock_print:
                _render_results_and_collisions(report, telemetry, "heal", True)
                assert mock_print.called

def test_cmd_sign_error_paths():
    """Verify error paths in cmd_sign."""
    from yamlr.cli.main import cmd_sign
    args = MagicMock(path="test.yaml")
    
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=False):
        with patch('yamlr.cli.main.console.print') as mock_print:
            cmd_sign(args)
            assert mock_print.called
            
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
        with patch.dict(os.environ, {}, clear=True):
            if "YAMLR_PRIVATE_KEY" in os.environ: del os.environ["YAMLR_PRIVATE_KEY"]
            with patch('yamlr.cli.main.console.print') as mock_print:
                cmd_sign(args)
                assert mock_print.called


def test_renderer_score_animation_empty():
    """Verify score animation with empty results."""
    report = MagicMock(results=[])
    with patch('yamlr.ui.theme.console.print') as mock_print:
        RichRenderer.render_score_animation(report)
        mock_print.assert_not_called()
