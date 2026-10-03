"""End-to-End Tests for SARIF and JSON Export Formats."""
import json
import os
import shutil
import tempfile
from pathlib import Path

from yamlr.cli.pipeline import _export_json_report, execute_pipeline, initialize_engine
from yamlr.sarif_reporter import SarifReporter

FIXTURES_DIR = str(Path(__file__).parent / "fixtures")


def test_e2e_json_report_generation():
    """E2E: Validates structured JSON report generation."""
    temp_dir = tempfile.mkdtemp(prefix="yamlr_json_test_")
    try:
        schemas = initialize_engine("1.30")
        report = execute_pipeline(FIXTURES_DIR, schemas, quiet=True)

        json_out = os.path.join(temp_dir, "report.json")
        _export_json_report(report, json_out)

        assert os.path.exists(json_out)
        with open(json_out, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "total_files" in data
        assert "total_time_ms" in data
        assert "results" in data
        assert isinstance(data["results"], list)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_e2e_sarif_report_generation():
    """E2E: Validates SARIF report generation."""
    temp_dir = tempfile.mkdtemp(prefix="yamlr_sarif_test_")
    try:
        schemas = initialize_engine("1.30")
        report = execute_pipeline(FIXTURES_DIR, schemas, quiet=True)

        sarif_out = os.path.join(temp_dir, "report.sarif")
        SarifReporter.generate_sarif(report.results, sarif_out)

        assert os.path.exists(sarif_out)
        with open(sarif_out, "r", encoding="utf-8") as f:
            sarif_data = json.load(f)

        assert sarif_data.get("version") == "2.1.0"
        assert "runs" in sarif_data
        assert len(sarif_data["runs"]) > 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
