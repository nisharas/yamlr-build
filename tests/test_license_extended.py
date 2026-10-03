from unittest.mock import patch

from yamlr.core_logic import LicenseManager


def test_license_load_env():
    """Verify loading from YAMLR_TOKEN."""
    with patch.dict('os.environ', {'YAMLR_TOKEN': 'test-token'}):
        with patch('yamlr_native.native_verify_token', return_value=True):
            lm = LicenseManager()
            assert lm.is_pro is True

def test_license_load_keyring():
    """Verify loading from keyring."""
    with patch('keyring.get_password', return_value='test-token'):
        with patch('yamlr_native.native_verify_token', return_value=True):
            lm = LicenseManager()
            assert lm.is_pro is True

def test_license_save_token_uses_only_os_credential_store():
    """Credential storage must not derive encryption keys from machine IDs."""
    with patch('keyring.set_password') as set_password:
        lm = LicenseManager()
        assert lm._save_token("raw-token") is True

    set_password.assert_called_once_with("yamlr", "session_token", "raw-token")


def test_license_save_token_fails_closed_when_credential_store_unavailable():
    with patch('keyring.set_password', side_effect=RuntimeError("no secure backend")):
        lm = LicenseManager()
        assert lm._save_token("raw-token") is False


def test_offline_activation_does_not_claim_success_when_storage_fails():
    with patch.object(LicenseManager, "verify_token", return_value=True):
        with patch.object(LicenseManager, "_save_token", return_value=False):
            lm = LicenseManager()
            assert lm.activate_offline_key("valid-token") is False
            assert lm.is_pro is False

