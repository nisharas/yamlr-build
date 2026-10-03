"""Tests for Core Exceptions and Resilient Error Handling."""
import logging

from yamlr.core.exceptions import (
    DiscoveryError,
    HealingError,
    LicenseError,
    NativeCoreError,
    SchemaLoadError,
    YamlrError,
)
from yamlr.core.scanner import streaming_scan


def test_exception_hierarchy():
    """Validates that all domain exceptions derive from YamlrError."""
    assert issubclass(NativeCoreError, YamlrError)
    assert issubclass(SchemaLoadError, YamlrError)
    assert issubclass(HealingError, YamlrError)
    assert issubclass(LicenseError, YamlrError)
    assert issubclass(DiscoveryError, YamlrError)
    assert issubclass(YamlrError, Exception)


def test_streaming_scan_nonexistent_path_resilience(caplog):
    """Validates scanner handles nonexistent paths gracefully."""
    with caplog.at_level(logging.DEBUG):
        results = list(streaming_scan("non_existent_folder_path_xyz_123", []))
    assert results == []
