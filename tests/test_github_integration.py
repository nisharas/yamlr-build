#!/usr/bin/env python3
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core.advisory import GitHubAdvisoryRenderer
from yamlr.models import HealAction, HealFileResult


def test_github_advisory_renderer_no_findings():
    renderer = GitHubAdvisoryRenderer()
    result = HealFileResult(
        file_path="service.yaml",
        full_path="service.yaml",
        success=True,
        status="UNCHANGED",
        kind="Service",
        logic_logs=[],
        findings=[],
        dna_integrity_score=100,
        identities=[],
    )

    comment = renderer.render_comment([result], is_dry_run=True)
    assert "## ✅ Yamlr Scan Report" in comment
    assert "Issues Detected** | 0" in comment
    assert "Findings" not in comment


def test_github_advisory_renderer_with_findings():
    renderer = GitHubAdvisoryRenderer()
    result = HealFileResult(
        file_path="broken.yaml",
        full_path="broken.yaml",
        success=True,
        status="PREVIEW",
        kind="Deployment",
        logic_logs=[],
        findings=[
            {
                "rule_id": "rule/no-limits",
                "message": "Missing resource limits",
                "severity": "warning",
                "rationale": "Safety first",
            }
        ],
        dna_integrity_score=45,
        identities=[],
    )

    comment = renderer.render_comment([result], is_dry_run=True)
    assert "## ⚠️ Yamlr Scan Report" in comment
    assert "Issues Detected** | 1" in comment
    assert "🔍 Finding Details" in comment
    assert "#### 📄 `broken.yaml` (Deployment)" in comment
    assert "⚠️ **WARNING** **rule/no-limits**: Missing resource limits" in comment


@patch("yamlr.core.integrations.github.urllib.request.urlopen")
def test_github_pr_client_create(mock_urlopen):
    from yamlr.core.integrations.github import GitHubPRClient

    # Mock response
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"id": 123, "body": "test"}'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    client = GitHubPRClient(token="fake", repository="owner/repo", pr_number=1)
    res = client.create_comment("hello")

    assert res["id"] == 123
    assert mock_urlopen.called
    args, _ = mock_urlopen.call_args
    req = args[0]
    assert req.get_full_url() == "https://api.github.com/repos/owner/repo/issues/1/comments"
    assert req.get_method() == "POST"


if __name__ == "__main__":
    pytest.main([__file__])
