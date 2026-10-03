"""Unit tests for Cryptographic Evidence Vault."""
import pytest

from yamlr.core.evidence_vault import COMPLIANCE_FRAMEWORKS, calculate_sha256, generate_receipt, verify_receipt


def test_calculate_sha256():
    data = "apiVersion: v1\nkind: Pod"
    h1 = calculate_sha256(data)
    h2 = calculate_sha256(data)
    assert h1 == h2
    assert len(h1) == 64


def test_generate_and_verify_receipt():
    manifest = "deploy.yaml"
    before = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  replicas: 1"
    after = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  replicas: 3"
    rules = ["SEC-001", "OPS-002"]

    receipt = generate_receipt(manifest, before, after, rules)
    assert receipt["manifest"] == "deploy.yaml"
    assert receipt["mutation_occurred"] is True
    assert "signature" in receipt
    assert "SOC2" in receipt["compliance_controls"]

    # Verify validity
    assert verify_receipt(receipt) is True

    # Verify tampering detection
    tampered = dict(receipt)
    tampered["dna_after"] = "bad-hash-00000000000000000000000000000000000000000000000000000000"
    assert verify_receipt(tampered) is False


def test_custom_secret_key_receipt():
    custom_key = b"enterprise-custom-hmac-secret-key"
    receipt = generate_receipt("service.yaml", "a: 1", "a: 2", ["REL-001"], secret_key=custom_key)
    assert verify_receipt(receipt, secret_key=custom_key) is True
    # Fails with wrong key
    assert verify_receipt(receipt, secret_key=b"wrong-key") is False


def test_production_enforcement_missing_key(monkeypatch):
    from yamlr.core.evidence_vault import get_signing_key

    # Simulate production/CI environment where pytest marker is not present and no key is configured
    monkeypatch.delenv("YAMLR_SIGNING_KEY", raising=False)
    monkeypatch.delenv("YAMLR_ALLOW_DEV_SIGNING", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("YAMLR_TEST_MODE", raising=False)

    with pytest.raises(ValueError, match="Cryptographic signing key missing"):
        get_signing_key(secret_key=None, allow_dev_fallback=False)

    # When YAMLR_SIGNING_KEY is provided, it succeeds
    monkeypatch.setenv("YAMLR_SIGNING_KEY", "vault-production-key-123")
    assert get_signing_key(secret_key=None) == b"vault-production-key-123"

