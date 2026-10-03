import os
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core_logic import LicenseManager


def test_license_manager_mid():
    """Verify machine ID generation."""
    with patch('yamlr_native.native_get_machine_id', return_value="test-mid"):
        lm = LicenseManager()
        assert lm.mid == "test-mid"

def test_license_manager_check_pro_no_token():
    """Check pro returns False if no token is found."""
    with patch('keyring.get_password', return_value=None):
        with patch('os.path.exists', return_value=False):
            lm = LicenseManager()
            assert lm.check_pro() is False

def test_license_manager_verify_heartbeat():
    """Verify heartbeat verification logic."""
    lm = LicenseManager()
    # Mocking native_verify_token to return True
    with patch('yamlr_native.native_verify_token', return_value=True):
        assert lm.verify_token("fake-token") is True

