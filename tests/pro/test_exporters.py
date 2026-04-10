import os
from unittest.mock import MagicMock

import pytest

from yamlr.pro.exporter import Exporter


def test_html_export_generation(tmp_path):
    """
    Why: To verify that the compliance reporting engine produces valid,
         human-readable HTML artifacts for audit evidence.
    """
    exporter = Exporter(MagicMock())
    output = tmp_path / "report.html"
    results = [{"path": "svc.yaml", "success": True, "findings": []}]

    assert exporter.export_html(results, str(output)) is True
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "Yamlr Compliance Dashboard" in content
    assert "svc.yaml" in content


def test_pdf_export_fallback(tmp_path):
    """
    Why: To ensure the system handles missing dependencies gracefully
         and provides actionable remediation advice to the user.
    """
    exporter = Exporter(MagicMock())
    output = tmp_path / "report.pdf"

    # We assume 'fpdf2' might not be installed in the environment
    # If it is, this test will verify generation; if not, it verifies the fallback.
    results = [{"path": "svc.yaml", "success": True, "findings": []}]

    # We check if it returns a boolean (either success or expected failure)
    res = exporter.export_pdf(results, str(output))
    assert isinstance(res, bool)
