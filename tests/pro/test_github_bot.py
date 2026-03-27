import os
import json
import pytest
from unittest.mock import patch, MagicMock
from yamlr.cli.github_bot import post_pr_comment, _generate_diff_summary

@pytest.fixture
def mock_reports():
    return [
        {
            "file_path": "deployment.yml",
            "health_score": 85,
            "findings": [
                {"rule_id": "SEC-001", "severity": "ERROR", "message": "Missing limits"}
            ],
            "raw_content": "apiVersion: v1\nkind: Deployment\nmetadata:\n  name: foo\n",
            "healed_content": "apiVersion: v1\nkind: Deployment\nmetadata:\n  name: foo\nspec:\n  template:\n    spec:\n      containers:\n      - name: web\n        resources:\n          limits:\n            memory: 512Mi\n"
        }
    ]

@patch("yamlr.core.bridge.YamlrBridge.is_offline_mode")
@patch("urllib.request.urlopen")
@patch("os.path.exists")
def test_post_pr_comment_full_flow(mock_exists, mock_urlopen, mock_offline, mock_reports):
    # Mock environment
    mock_offline.return_value = False
    with patch.dict(os.environ, {
        "GITHUB_TOKEN": "secret-token",
        "GITHUB_EVENT_PATH": "/tmp/event.json",
        "GITHUB_ACTIONS": "true"
    }):
        mock_exists.return_value = True
        
        # Mock event data
        event_data = {
            "pull_request": {"number": 123},
            "repository": {"full_name": "yamlr/test-repo"}
        }
        
        with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=lambda s: s, read=lambda: json.dumps(event_data)))):
             # Mock the file read to return a file-like object that gives json
             with patch("json.load", return_value=event_data):
                post_pr_comment(mock_reports)
        
        # Verify urlopen was called with a request containing the expected body
        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        body = req.data.decode("utf-8")
        
        # Check for key text components, avoiding emoji encoding issues in assertions
        assert "Yamlr Guard Security & Health Report" in body
        assert "Proposed Repairs (Diff Summary)" in body
        assert "Fix Preview" in body
        assert "deployment.yml" in body

def test_generate_diff_summary_truncation():
    # Test that truncation logic works
    reports = [
        {
            "file_path": f"file_{i}.yml",
            "raw_content": "old",
            "healed_content": "new"
        } for i in range(10)
    ]
    
    # Set a very small max_length to trigger truncation
    summary = _generate_diff_summary(reports, max_length=200)
    assert "Remaining diffs truncated" in summary
    assert "Fix Preview" in summary

def test_generate_diff_summary_no_changes():
    reports = [
        {
            "file_path": "clean.yml",
            "raw_content": "same",
            "healed_content": "same"
        }
    ]
    summary = _generate_diff_summary(reports)
    assert summary == ""
