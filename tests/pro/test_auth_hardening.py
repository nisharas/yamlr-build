import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from yamlr.pro.auth import AuthManager


@pytest.fixture
def keys():
    # Generate RS256 keys for test
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return priv_pem, pub_pem


def test_auth_validate_session_rs256(keys):
    priv_pem, pub_pem = keys
    auth = AuthManager(app_name="YamlrTest")

    # Create valid token
    payload = {"sub": "user_123", "iss": "yamlr-auth", "tier": "enterprise", "exp": time.time() + 3600}
    token = jwt.encode(payload, priv_pem, algorithm="RS256")

    with (
        patch.object(auth, "get_token", return_value=token),
        patch.object(auth, "_get_public_key", return_value=pub_pem),
    ):
        assert auth.validate_session() is True


def test_auth_validate_session_expired(keys):
    priv_pem, pub_pem = keys
    auth = AuthManager(app_name="YamlrTest")

    # Create expired token
    payload = {"sub": "user_123", "iss": "yamlr-auth", "tier": "enterprise", "exp": time.time() - 3600}
    token = jwt.encode(payload, priv_pem, algorithm="RS256")

    with (
        patch.object(auth, "get_token", return_value=token),
        patch.object(auth, "_get_public_key", return_value=pub_pem),
    ):
        assert auth.validate_session() is False


def test_auth_validate_session_invalid_issuer(keys):
    priv_pem, pub_pem = keys
    auth = AuthManager(app_name="YamlrTest")

    # Create token with wrong issuer
    payload = {"sub": "user_123", "iss": "wrong-issuer", "tier": "enterprise", "exp": time.time() + 3600}
    token = jwt.encode(payload, priv_pem, algorithm="RS256")

    with (
        patch.object(auth, "get_token", return_value=token),
        patch.object(auth, "_get_public_key", return_value=pub_pem),
    ):
        assert auth.validate_session() is False


def test_auth_validate_session_invalid_tier(keys):
    priv_pem, pub_pem = keys
    auth = AuthManager(app_name="YamlrTest")

    # Create token with wrong tier
    payload = {"sub": "user_123", "iss": "yamlr-auth", "tier": "free", "exp": time.time() + 3600}
    token = jwt.encode(payload, priv_pem, algorithm="RS256")

    with (
        patch.object(auth, "get_token", return_value=token),
        patch.object(auth, "_get_public_key", return_value=pub_pem),
    ):
        assert auth.validate_session() is False
