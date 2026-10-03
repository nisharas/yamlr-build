import os
from unittest.mock import MagicMock, patch
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from yamlr.cli.main import run_standalone
from yamlr.cli.signing import canonicalize_manifest_for_signing


def test_cli_sign_dispatch():
    """Verify sign command dispatch."""
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
        with patch('sys.argv', ['yamlr', 'sign', 'test.yaml']):
            with patch('yamlr.cli.main.cmd_sign') as mock_sign:
                run_standalone()
                mock_sign.assert_called_once()


def test_cli_verify_dispatch():
    """Verify verify command dispatch."""
    with patch('yamlr.core_logic.LicenseManager.check_pro', return_value=True):
        with patch('sys.argv', ['yamlr', 'verify', 'test.yaml']):
            with patch('yamlr.cli.main.cmd_verify') as mock_verify:
                run_standalone()
                mock_verify.assert_called_once()


def test_real_manifest_signing_and_verification(tmp_path, monkeypatch):
    """End-to-end cryptographic signing and verification of a Kubernetes manifest."""
    # Generate an ephemeral RSA key pair for testing
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    manifest = tmp_path / "app.yaml"
    manifest.write_text(
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: payment-service\nspec:\n  replicas: 3\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("YAMLR_PRIVATE_KEY", private_pem)

    with patch("yamlr.core_logic.LicenseManager.check_pro", return_value=True), \
         patch("yamlr.core_logic.LicenseManager._get_pubkey", return_value=public_pem):
        # 1. Sign manifest
        with patch("sys.argv", ["yamlr", "sign", str(manifest)]):
            run_standalone()

        signed_content = manifest.read_text(encoding="utf-8")
        assert "yamlr.dev/signature" in signed_content

        # 2. Verify intact manifest (must succeed)
        with patch("sys.argv", ["yamlr", "verify", str(manifest)]):
            run_standalone()

        # 3. Tamper with manifest (tampered replica count) -> verify must detect tampering and exit 1
        tampered = signed_content.replace("replicas: 3", "replicas: 100")
        manifest.write_text(tampered, encoding="utf-8")
        with patch("sys.argv", ["yamlr", "verify", str(manifest)]):
            with pytest.raises(SystemExit) as excinfo:
                run_standalone()
            assert excinfo.value.code == 1

