from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import audit_topology_outages


def test_audit_topology_outages_cycle():
    """Verify topology outage audit detects circular dependencies."""
    mock_res1 = MagicMock()
    mock_res1.identity = MagicMock()
    mock_res2 = MagicMock()
    mock_res2.identity = MagicMock()
    
    mock_native = MagicMock()
    mock_native.native_build_topology_graph.return_value = ["edge1", "edge2"]
    mock_native.native_detect_circular_dependencies.return_value = ["Circular dependency detected"]
    mock_native.native_detect_dangling_selectors.return_value = []
    mock_native.native_detect_orphaned_resources.return_value = []
    mock_native.native_detect_service_shadowing.return_value = []
    mock_native.native_detect_version_drift.return_value = []
    
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        findings = audit_topology_outages([mock_res1, mock_res2])
        assert len(findings) > 0
        assert findings[0]["type"] == "Circular Dependency"
        assert findings[0]["msg"] == "Circular dependency detected"
