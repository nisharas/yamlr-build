from unittest.mock import MagicMock, patch

import pytest

import os
from yamlr.core_logic import _calculate_health_score, _collect_yaml_files, audit_topology_outages



def test_calculate_health_score():
    """Verify health score math."""
    v1 = MagicMock(severity="CRITICAL")
    v2 = MagicMock(severity="HIGH")
    v3 = MagicMock(severity="MEDIUM")
    v4 = MagicMock(severity="LOW")
    
    # 100 - 15 - 5 - 2 - 0.5 = 77.5
    assert _calculate_health_score([v1, v2, v3, v4]) == 77.5
    assert _calculate_health_score([]) == 100.0

def test_audit_topology_outages():
    """Verify topology audit logic."""
    res1 = MagicMock()
    res1.identity = MagicMock()
    res2 = MagicMock()
    res2.identity = MagicMock()
    
    mock_native = MagicMock()
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        audit_topology_outages([res1, res2])
        mock_native.native_build_topology_graph.assert_called_once()

def test_collect_yaml_files(temp_workspace):
    """Verify YAML collection logic."""
    f1 = os.path.join(temp_workspace, "a.yaml")
    f2 = os.path.join(temp_workspace, "b.yml")
    f3 = os.path.join(temp_workspace, "c.txt")
    with open(f1, 'w') as f: f.write("")
    with open(f2, 'w') as f: f.write("")
    with open(f3, 'w') as f: f.write("")
    
    files = _collect_yaml_files(temp_workspace)
    assert len(files) == 2
    assert any(f.endswith("a.yaml") for f in files)
    assert any(f.endswith("b.yml") for f in files)
