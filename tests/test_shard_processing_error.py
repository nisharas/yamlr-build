from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import _process_document_shards


def test_process_document_shards_error():
    """Verify error handling in document shard processing."""
    mock_native = MagicMock()
    mock_native.native_audit_forensics.side_effect = Exception("Structurize Error")
    
    # Call _process_document_shards
    _process_document_shards(mock_native, "test.yaml", [], [], "content")
    
    # Check if ResourceResult was called with integrity_violations=[]
    args, kwargs = mock_native.ResourceResult.call_args
    assert kwargs['integrity_violations'] == []
