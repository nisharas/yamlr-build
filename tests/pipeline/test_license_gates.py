import pytest

from yamlr.core.exceptions import YamlrQuotaError
from yamlr.pro.license import license_manager


def test_license_gate_enforcement():
    """
    Verifies that LicenseManager.feature_gate correctly blocks unauthorized flags.
    Why: To ensure that Enterprise/Pro features are not accessible in the OSS tier.
    """
    # Mock free tier
    original_fn = license_manager._get_payload
    license_manager._get_payload = lambda: {"tier": "free"}

    try:
        # Should raise error for 'enterprise' features
        with pytest.raises(YamlrQuotaError) as exc:
            license_manager.feature_gate("sovereign", "test-context")
        assert "requires Enterprise license" in str(exc.value)

        # Should raise error for 'pro' features in free tier
        with pytest.raises(YamlrQuotaError) as exc:
            license_manager.feature_gate("deep_validate", "test-context")
        assert "requires Pro license" in str(exc.value)

    finally:
        license_manager._get_payload = original_fn


def test_license_gate_authorized():
    """Verifies that licensed features pass through the gate."""
    # Mock pro tier
    original_fn = license_manager._get_payload
    license_manager._get_payload = lambda: {"tier": "pro"}

    try:
        # Should NOT raise error for 'pro' features
        license_manager.feature_gate("deep_validate", "test-context")

        # Should still raise error for 'enterprise' features in pro tier
        with pytest.raises(YamlrQuotaError) as exc:
            license_manager.feature_gate("sovereign", "test-context")
        assert "requires Enterprise license" in str(exc.value)
    finally:
        license_manager._get_payload = original_fn
