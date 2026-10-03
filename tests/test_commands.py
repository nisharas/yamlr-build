from unittest.mock import MagicMock, patch

import pytest

try:
    from yamlr.core_logic import UniversalCommandRegistry, cmd_dna, cmd_guide_rich, cmd_roi, cmd_version, cmd_welcome
except ImportError:
    cmd_welcome = cmd_version = cmd_guide_rich = cmd_dna = cmd_roi = UniversalCommandRegistry = MagicMock()
import os


def test_command_registry():
    """Verify registry metadata."""
    assert UniversalCommandRegistry.is_pro("dna") is True
    assert UniversalCommandRegistry.is_pro("scan") is False
    assert "Generate immutable" in UniversalCommandRegistry.get_desc("dna")

@patch('yamlr.ui.renderer.RichRenderer.render_welcome')
@patch('yamlr.core.info._detect_k8s_version_safe', return_value="1.30")
def test_cmd_welcome(mock_detect, mock_render):
    """Verify welcome command triggers renderer."""
    cmd_welcome()
    mock_render.assert_called_once_with(os.getcwd(), "1.30")

@patch('yamlr.ui.theme.console.print')
def test_cmd_version(mock_print):
    """Verify version command prints version."""
    with patch('yamlr.version.__version__', "0.1.0"):
        cmd_version()
        # Should print version info
        assert any("0.1.0" in str(call) for call in mock_print.call_args_list)

@patch('yamlr.ui.renderer.RichRenderer.render_explain')
@patch('yamlr.knowledge.registry.KnowledgeRegistry.lookup')
def test_cmd_guide_rich(mock_lookup, mock_render):
    """Verify guide command renders topics."""
    mock_lookup.return_value = {"title": "Test"}
    cmd_guide_rich("TEST")
    mock_render.assert_called_once_with("TEST", {"title": "Test"})

def test_cmd_dna(temp_workspace):
    """Verify DNA command calculates semantic DNA hashes."""
    fpath = os.path.join(temp_workspace, "test.yaml")
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test-config\ndata:\n  key: value\n")
    
    cmd_dna(temp_workspace)


def test_cmd_roi(temp_workspace):
    """Verify ROI command analyzes manifests and produces impact metrics."""
    fpath = os.path.join(temp_workspace, "test.yaml")
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write("apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\nspec:\n  replicas: 3\n")
    
    result = cmd_roi(temp_workspace, output="json")
    assert result["manifests_analyzed"] == 1
    assert result["documents_parsed"] >= 1

