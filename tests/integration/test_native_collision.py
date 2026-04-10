import pytest

from yamlr.parsers.lexer import YamlrLexer
from yamlr.parsers.scanner import YamlrScanner


def test_native_collision_regression():
    """
    Test that the Native Scanner (via fast_scan wrapper) correctly falls back
    to Python when an identity collision (duplicate kind keys) is detected.
    """
    content = """
kind: Deployment
apiVersion: apps/v1
metadata:
  name: collision-test
kind: Service
apiVersion: v1
metadata:
  name: collision-test
"""
    # Native Scanner (Now with Python safety wrapper)
    scanner = YamlrScanner()
    native_results = scanner.fast_scan(content)

    # Python Scanner (Explicitly Shard-based)
    lexer = YamlrLexer()
    shards = lexer.shard(content)
    python_results = scanner.scan_shards(shards)

    # Both should detect the collision (Python scanner rejects document)
    assert len(native_results) == 0, f"Native scanner failed to detect identity collision. Got: {native_results}"
    assert len(python_results) == 0


def test_multi_doc_collision():
    content = """
kind: Pod
apiVersion: v1
metadata:
  name: pod-1
---
kind: Service
metadata:
  name: collision-2
kind: Service
metadata:
  name: collision-2
"""
    scanner = YamlrScanner()
    native_results = scanner.fast_scan(content)

    # Document 2 should be rejected.
    assert len(native_results) == 1, (
        f"Native scanner should have only found 1 valid document, but found {len(native_results)}"
    )
    assert native_results[0].name == "pod-1"
