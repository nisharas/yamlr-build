"""End-to-End Tests for CLI Pipeline and Streaming Scanner."""
import os
from pathlib import Path

import pytest

from yamlr.cli.pipeline import detect_version, execute_pipeline, initialize_engine
from yamlr.core.scanner import streaming_scan

FIXTURES_DIR = str(Path(__file__).parent / "fixtures")


def test_e2e_pipeline_execution():
    """E2E: Executes the full pipeline on test fixtures with real native engine."""
    schemas = initialize_engine("1.30")
    assert isinstance(schemas, list)

    report = execute_pipeline(FIXTURES_DIR, schemas, quiet=True)
    assert report is not None
    assert report.total_files >= 1
    assert len(report.results) >= 1

    # Verify at least one result has identity extracted
    identities = [r.identity for r in report.results if r.identity]
    assert len(identities) > 0


def test_e2e_streaming_scan_real_disk():
    """E2E: Validates generator stream over real fixture files."""
    schemas = initialize_engine("1.30")
    results = list(streaming_scan(FIXTURES_DIR, schemas))

    assert len(results) > 0
    for res in results:
        assert hasattr(res, "file_path")
        assert os.path.exists(res.file_path)
        assert hasattr(res, "health_score")
        assert 0.0 <= res.health_score <= 100.0


def test_e2e_detect_version_fallback():
    """E2E: Ensures detect_version returns a valid semver-like string."""
    version = detect_version()
    assert isinstance(version, str)
    assert len(version) >= 3
