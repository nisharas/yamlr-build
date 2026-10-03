from unittest.mock import MagicMock, patch

import pytest

from yamlr.cli.handlers import _cmd_admin

def test_cmd_admin_health():
    """Verify admin health check."""
    _cmd_admin("health")

def test_cmd_admin_stats():
    """Verify admin stats check."""
    with patch('urllib.request.urlopen') as mock_url:
        mock_url.return_value.__enter__.return_value.read.return_value = b'{"mrr_growth": "10%", "active_licenses": 100, "forensic_events": 50}'
        _cmd_admin("stats")

def test_cmd_admin_users():
    """Verify admin users check."""
    _cmd_admin("users")
