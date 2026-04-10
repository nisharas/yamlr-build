import hashlib
import json
from pathlib import Path

import pytest

from yamlr.core.license_manager import LicenseManager, ProStatus


def test_quota_hardening_tamper_detection(tmp_path, monkeypatch):
    """
    Why: To ensure that the monetization integrity is preserved even if a user
         manually attempts to bypass limits.
    """
    quota_file = tmp_path / "quota.json"
    monkeypatch.setattr(LicenseManager, "get_quota_path", lambda: quota_file)

    # 1. Create a valid quota file
    LicenseManager.record_healing_usage(2)
    assert quota_file.exists()

    with open(quota_file, "r") as f:
        data = json.load(f)

    # Verify initial state
    allowed, remaining, _ = LicenseManager.is_healing_allowed(1)
    assert allowed is True
    assert remaining == 3

    # 2. Tamper with the file (manually reset usage)
    data["usage"] = 0
    # Note: we don't update the signature
    with open(quota_file, "w") as f:
        json.dump(data, f)

    # 3. Verify that tampering is detected and conservative limit is applied
    # The logic in LicenseManager.is_healing_allowed should detect sig mismatch
    # and treat it as limit reached.
    allowed, remaining, _ = LicenseManager.is_healing_allowed(1)
    assert allowed is False  # Tampering forces conservative limit (limit reached)
    assert remaining == 0


def test_license_status_mapping():
    """
    Why: To ensure different validation reasons are correctly mapped to UI-visible ProStatus.
    """
    from unittest.mock import patch

    from yamlr.pro import license as pro_license

    with patch("yamlr.pro.license.auth_device") as mock_auth:
        # Mock invalid session
        mock_auth.validate_session.return_value = False
        valid, msg = pro_license.validate()
        assert valid is False
        assert "Unauthenticated" in msg

        # Test LicenseManager mapping
        status, reason = LicenseManager.check_pro_status()
        assert status == ProStatus.LICENSE_INVALID
        assert "Unauthenticated" in reason
