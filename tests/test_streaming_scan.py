import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import streaming_scan


def test_streaming_scan_logic(temp_workspace):
    """Verify streaming scan processing logic."""
    f1 = os.path.join(temp_workspace, "test.yaml")
    with open(f1, 'w') as f: f.write("apiVersion: v1\nkind: Pod\nmetadata:\n  name: test")
    
    mock_native = MagicMock()
    mock_shard = MagicMock(is_doc_boundary=False)
    mock_native.native_shard.return_value = [mock_shard]
    mock_native.extract_native_identity.return_value = MagicMock()
    mock_native.native_structurize.return_value = MagicMock(integrity_violations=[])
    mock_native.ResourceResult.return_value = MagicMock(path="test.yaml")
    
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        gen = streaming_scan(f1, [])
        results = list(gen)
        assert len(results) == 1
        mock_native.native_shard.assert_called_once()
        mock_native.extract_native_identity.assert_called_once()

def test_streaming_scan_empty_file(temp_workspace):
    """Verify streaming scan handles empty files."""
    f1 = os.path.join(temp_workspace, "empty.yaml")
    with open(f1, 'w') as f: f.write("")
    
    mock_native = MagicMock()
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        gen = streaming_scan(f1, [])
        results = list(gen)
        assert len(results) == 0
