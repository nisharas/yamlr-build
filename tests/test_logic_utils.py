import json
import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import _collect_yaml_files, _detect_k8s_version_safe, _print_available_topics

def test_collect_yaml_files(temp_workspace):
    """Verify recursive YAML collection."""
    # Create structure
    os.makedirs(os.path.join(temp_workspace, "subdir"))
    f1 = os.path.join(temp_workspace, "root.yaml")
    f2 = os.path.join(temp_workspace, "subdir", "child.yml")
    f3 = os.path.join(temp_workspace, "ignore.txt")
    
    for f in [f1, f2, f3]:
        with open(f, 'w') as fh: fh.write("content")
        
    files = _collect_yaml_files(temp_workspace)
    assert len(files) == 2
    assert f1 in files
    assert any(f2 in f for f in files) # Handle path separators

@patch('os.getenv', return_value="1.29")
def test_detect_k8s_version_env(mock_env):
    """Verify version detection from env."""
    assert _detect_k8s_version_safe() == '1.29'

@patch('os.getenv', return_value=None)
@patch('subprocess.run')
@patch('yamlr_native.native_detect_cluster_version', side_effect=RuntimeError("No cluster found"))
def test_detect_k8s_version_kubectl(mock_native, mock_run, mock_env):
    """Verify version detection from kubectl when native detector falls back."""
    mock_run.return_value = MagicMock(
        returncode=0, 
        stdout=json.dumps({"clientVersion": {"major": "1", "minor": "28"}})
    )
    assert _detect_k8s_version_safe() == "1.28"


@patch('yamlr.ui.theme.console.print')
def test_print_available_topics(mock_print):
    """Verify print_available_topics renders table."""
    mock_registry = MagicMock()
    mock_registry.DATA = {"Y-101": {"title": "Test Topic"}}
    _print_available_topics(mock_registry)
    mock_print.assert_called()
