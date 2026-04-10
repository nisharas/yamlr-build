from unittest.mock import MagicMock, patch

import pytest

from yamlr.pro.auth import AuthManager


def test_device_auth_flow_plumbing():
    """
    Why: To verify that the multi-step OIDC device flow logic is correctly
         sequenced, from code request to token polling.
    """
    auth = AuthManager()

    with patch.object(auth, "_request_device_code") as mock_req, patch.object(auth, "_poll_for_token") as mock_poll:
        mock_req.return_value = {
            "device_code": "dev_123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://auth.yamlr.dev/activate",
            "expires_in": 300,
            "interval": 1,
        }
        mock_poll.return_value = True

        # Note: We don't want to actually open a browser during tests
        with patch("webbrowser.open"):
            assert auth.login() is True
            mock_req.assert_called_once()
            # In auth.py we used _ as the name for the first param to resolve unused lint
            # but mock verify still checks positions.
            mock_poll.assert_called()
