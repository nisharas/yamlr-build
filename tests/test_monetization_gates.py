import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from yamlr.core.license_manager import LicenseManager

@patch("yamlr.core.license_manager.LicenseManager.check_pro_status")
def test_habit_gate_blocks_over_5_files(mock_pro, tmp_path):
    # Simulate OSS Mode
    mock_pro.return_value = (MagicMock(is_usable=lambda: False), "OSS Mode")
    quota_file = tmp_path / "test_quota.json"

    with patch("yamlr.core.license_manager.LicenseManager.get_quota_path", return_value=quota_file):
        # 1. 6 files in one batch should fail instantly
        allowed, rem, msg = LicenseManager.check_healing_quota(6)
        assert allowed is False
        assert rem == 0
        assert "limited to 5 files" in msg
        assert not quota_file.exists()

        # 2. 3 files should pass, 2 remaining
        allowed, rem, msg = LicenseManager.check_healing_quota(3)
        assert allowed is True
        assert rem == 2
        
        # Verify it wrote to JSON
        assert quota_file.exists()
        data = json.loads(quota_file.read_text())
        assert data["usage"] == 3

        # 3. 3 more files should fail (exceeds 5)
        allowed, rem, msg = LicenseManager.check_healing_quota(3)
        assert allowed is False
        assert rem == 2  # Still 2 remaining

        # 4. 2 more files should pass exactly
        allowed, rem, msg = LicenseManager.check_healing_quota(2)
        assert allowed is True
        assert rem == 0
        
        # 5. 1 more file should fail (zero remaining)
        allowed, rem, msg = LicenseManager.check_healing_quota(1)
        assert allowed is False
        assert rem == 0

@patch("yamlr.core.license_manager.LicenseManager.check_pro_status")
def test_habit_gate_bypassed_for_pro(mock_pro, tmp_path):
    # Simulate PRO Mode
    mock_pro.return_value = (MagicMock(is_usable=lambda: True), "Pro Active")
    
    with patch("yamlr.core.license_manager.LicenseManager.get_quota_path", return_value=tmp_path / "x"):
        allowed, rem, msg = LicenseManager.check_healing_quota(10000)
        assert allowed is True
        assert rem == -1
