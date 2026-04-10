from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core.pro.usage_limiter import UsageLimiter


def test_quota_recovery_on_date_change():
    """Verify that quota resets on a new day even if signature is invalid."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Mock stats with a corrupted signature from yesterday
    stats = {"quota_date": yesterday.isoformat(), "daily_heals_count": 5, "quota_sig": "corrupted-signature"}

    with patch("yamlr.core.telemetry.GlobalTelemetryManager") as mock_gtm:
        instance = mock_gtm.return_value
        instance.data = stats

        # Should allow healing 1 file because it's a new day
        allowed, remaining, msg = UsageLimiter.is_healing_allowed(1)
        assert allowed is True
        assert remaining == 5  # Resets to FULL limit on new day


def test_quota_enforcement_on_same_day_corrupt():
    """Verify that same-day corruption defaults to MAX limit (safe for business)."""
    today = date.today().isoformat()
    stats = {"quota_date": today, "daily_heals_count": 2, "quota_sig": "corrupted-signature"}

    with patch("yamlr.core.telemetry.GlobalTelemetryManager") as mock_gtm:
        instance = mock_gtm.return_value
        instance.data = stats

        # Should block healing because corruption on same day implies tampering
        allowed, remaining, msg = UsageLimiter.is_healing_allowed(1)
        assert allowed is False
        assert remaining == 0


if __name__ == "__main__":
    pytest.main([__file__])
