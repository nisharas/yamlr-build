import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import streaming_scan


def test_streaming_scan_multi_doc(temp_workspace):
    """Verify streaming scan handles multi-document YAML files."""
    yaml_path = os.path.join(temp_workspace, "multi.yaml")
    with open(yaml_path, 'w') as f:
        f.write("apiVersion: v1\nkind: Pod\nmetadata:\n  name: p1\n---\napiVersion: v1\nkind: Pod\nmetadata:\n  name: p2\n")
    
    mock_native = MagicMock()
    # Mock shard to return doc boundary
    s1 = MagicMock(is_doc_boundary=False)
    s2 = MagicMock(is_doc_boundary=True)
    s3 = MagicMock(is_doc_boundary=False)
    
    mock_native.native_shard.return_value = [s1, s2, s3]
    mock_native.extract_native_identity.return_value = MagicMock()
    mock_native.native_structurize.return_value = MagicMock()
    
    with patch.dict('sys.modules', {'yamlr_native': mock_native}):
        # We need to ensure _process_document_shards is called
        results = list(streaming_scan(yaml_path, []))
        # Should yield 2 results (one for each doc)
        # Wait, the logic is: process doc_shards when boundary found, OR at end.
        # [s1, s2] -> s2 is boundary. Yields result for s1.
        # [s3] -> end of file. Yields result for s3.
        assert len(results) == 2
