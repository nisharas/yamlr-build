import os
from unittest.mock import ANY, MagicMock, patch

import pytest

from yamlr.cli.main import execute_pipeline
from yamlr.core_logic import _process_document_shards, streaming_scan


def test_streaming_scan_single_file(temp_workspace):
    """Verify that streaming_scan handles a single file correctly."""
    yaml_path = os.path.join(temp_workspace, "test.yaml")
    with open(yaml_path, 'w') as f:
        f.write("apiVersion: v1\nkind: Pod\nmetadata:\n  name: test\n")
    
    mock_shard = MagicMock()
    mock_shard.is_doc_boundary = False
    
    with patch('yamlr_native.native_shard', return_value=[mock_shard]):
        with patch('yamlr.core.scanner._process_document_shards', return_value="mock-result") as mock_process:
            results = list(streaming_scan(yaml_path, []))
            assert len(results) == 1
            assert results[0] == "mock-result"
            mock_process.assert_called_once()

def test_streaming_scan_multi_doc(temp_workspace):
    """Verify that streaming_scan splits multi-document files."""
    yaml_path = os.path.join(temp_workspace, "multi.yaml")
    with open(yaml_path, 'w') as f:
        f.write("---\napiVersion: v1\nkind: Pod\n---\napiVersion: v1\nkind: Service\n")
    
    # Mock shards with doc boundaries
    shard1 = MagicMock()
    shard1.is_doc_boundary = True
    shard2 = MagicMock()
    shard2.is_doc_boundary = False
    shard3 = MagicMock()
    shard3.is_doc_boundary = True
    
    with patch('yamlr_native.native_shard', return_value=[shard1, shard2, shard3]):
        with patch('yamlr.core.scanner._process_document_shards', return_value="mock-result") as mock_process:
            results = list(streaming_scan(yaml_path, []))
            # Shard 1 is boundary (first doc starts), Shard 2 is content, Shard 3 is boundary (next doc starts)
            # Logic: yields on boundary if doc_shards is not empty.
            # Shard 1: doc_shards=[], nothing yielded. doc_shards=[shard1] (wait, logic says: if is_doc_boundary { if doc_shards { yield } doc_shards=[] } else { doc_shards.append })
            # Actually line 296: for shard in shards: if shard.is_doc_boundary: if doc_shards: yield; doc_shards=[] else: doc_shards.append(shard)
            # Plus a final yield after the loop.
            assert len(results) == 1 # Depending on the exact logic in core_logic.py
            # Let's check the logic again:
            # 296: for shard in shards:
            # 297:     if shard.is_doc_boundary:
            # 298:         if doc_shards:
            # 299:             result = _process_document_shards(...)
            # 303:             yield result
            # 304:             doc_shards = []
            # 305:     else:
            # 306:         doc_shards.append(shard)
            # 309: if doc_shards: yield _process_document_shards(...)
            
            # Shard 1: is_boundary=True, doc_shards=[] -> nothing. Loop continues. (Wait, shard 1 is NOT appended)
            # Shard 2: is_boundary=False -> doc_shards=[shard2]
            # Shard 3: is_boundary=True, doc_shards=[shard2] -> yield. doc_shards=[]
            # End of loop. doc_shards is empty.
            # Total: 1 yield.
            
def test_process_document_shards_scoring():
    """Verify health score calculation in _process_document_shards."""
    mock_native = MagicMock()
    mock_native.extract_native_identity.return_value = MagicMock(kind="Pod", name="test")
    
    # Mock violations
    v1 = MagicMock()
    v1.severity = "CRITICAL"
    v2 = MagicMock()
    v2.severity = "HIGH"
    mock_native.native_check_schema_violations.return_value = [v1, v2]
    
    mock_native.native_audit_forensics.return_value = []
    
    _process_document_shards(mock_native, "test.yaml", [], ["some-schema"], "content")
    
    # Check ResourceResult call
    args, kwargs = mock_native.ResourceResult.call_args
    assert kwargs['health_score'] == 80.0

def test_execute_pipeline_aggregation():
    """Verify that execute_pipeline aggregates streaming results into a report."""
    with patch('yamlr.core_logic.streaming_scan', return_value=[MagicMock(file_path="p1"), MagicMock(file_path="p2")]):
        with patch('yamlr_native.NativeReport') as mock_report_class:
            execute_pipeline("some/path", [])
            mock_report_class.assert_called_once()
            args, kwargs = mock_report_class.call_args
            assert kwargs['total_files'] == 2
            assert kwargs['results'] == [ANY, ANY]
