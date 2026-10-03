"""Ensure the reviewed SARIF schema enforces fields, levels, and locations."""

import pytest
from jsonschema import ValidationError

from scripts.ci.verify_report_contracts import validator


def test_official_schema_accepts_minimal_complete_sarif():
    validator().validate(
        {
            "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "Yamlr"}}, "results": []}],
        }
    )


@pytest.mark.parametrize(
    "report",
    [
        {"version": "2.1.0", "runs": [], "invented": True},
        {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "Yamlr"}},
                    "results": [{"message": {"text": "finding"}, "level": "critical"}],
                }
            ],
        },
        {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "Yamlr"}},
                    "graphs": [
                        {"id": "invalid-graph-property", "nodes": [], "edges": []}
                    ],
                }
            ],
        },
    ],
)
def test_official_schema_rejects_invalid_sarif(report):
    with pytest.raises(ValidationError):
        validator().validate(report)
