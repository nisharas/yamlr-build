"""Cryptographic Evidence Vault for SOC2, ISO 27001, and HIPAA compliance.

Generates tamper-evident, HMAC-signed audit receipts containing pre/post manifest
DNA signatures, evaluated compliance controls, and cryptographic proofs.
"""
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional


def get_signing_key(secret_key: Optional[bytes] = None, allow_dev_fallback: bool = False) -> bytes:
    """Returns the effective HMAC signing key from parameter, env, or deterministic dev key.

    Why: In production and audit environments, keys must be provided via parameter, secure vault,
         or environment variable (YAMLR_SIGNING_KEY) to guarantee cryptographic non-repudiation.
         Silently falling back to a static dev secret in CI/production is disallowed because it
         undermines the integrity of compliance receipts. Local dev fallback is permitted only
         when explicitly requested or during automated test execution.
    """
    if secret_key is not None:
        return secret_key
    env_key = os.environ.get("YAMLR_SIGNING_KEY")
    if env_key:
        return env_key.encode("utf-8")

    # In local test suites or explicit dev opt-in, use deterministic local entropy
    is_testing = "PYTEST_CURRENT_TEST" in os.environ or "YAMLR_TEST_MODE" in os.environ
    if allow_dev_fallback or is_testing or os.environ.get("YAMLR_ALLOW_DEV_SIGNING") == "1":
        return os.environ.get("YAMLR_DEV_KEY", "yamlr-dev-vault-local-entropy").encode("utf-8")

    raise ValueError(
        "Cryptographic signing key missing: YAMLR_SIGNING_KEY must be configured in environment "
        "or vault to generate verifiable compliance receipts. Set YAMLR_ALLOW_DEV_SIGNING=1 "
        "only for local offline development."
    )

COMPLIANCE_FRAMEWORKS = {
    "SOC2": [
        "CC6.1 - Logical and Physical Access Controls",
        "CC6.6 - Logical Boundary Protection",
        "CC7.1 - Configuration and Vulnerability Management"
    ],
    "CIS_K8S_v1_8": [
        "5.1.1 - Ensure image pull policies adhere to immutability standards",
        "5.2.1 - Minimize admission of privileged containers",
        "5.7.1 - Ensure default namespace is not actively used for workloads"
    ],
    "HIPAA_Security_Rule": [
        "164.312(a)(1) - Technical Safeguards: Access Control",
        "164.312(e)(1) - Technical Safeguards: Transmission Security"
    ]
}


def calculate_sha256(content: str) -> str:
    """Calculates SHA-256 hash of text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sign_payload(
    payload: Dict[str, Any],
    secret_key: Optional[bytes] = None,
    allow_dev_fallback: bool = False
) -> str:
    """Computes HMAC-SHA256 signature for canonical JSON payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    key = get_signing_key(secret_key, allow_dev_fallback=allow_dev_fallback)
    return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_receipt(
    manifest_path: str,
    content_before: str,
    content_after: str,
    rules_applied: List[str],
    secret_key: Optional[bytes] = None,
    allow_dev_fallback: bool = False
) -> Dict[str, Any]:
    """Generates an HMAC-signed compliance audit receipt for a manifest.

    Args:
        manifest_path: Relative or absolute path to the manifest.
        content_before: Manifest content prior to remediation.
        content_after: Manifest content after remediation.
        rules_applied: List of rule IDs remediated or audited.
        secret_key: HMAC signing key.
        allow_dev_fallback: Whether to allow fallback to dev secret if key is missing.

    Returns:
        Signed receipt dictionary.
    """
    dna_before = calculate_sha256(content_before)
    dna_after = calculate_sha256(content_after)

    payload = {
        "version": "1.0.0",
        "manifest": os.path.basename(manifest_path),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dna_before": dna_before,
        "dna_after": dna_after,
        "mutation_occurred": dna_before != dna_after,
        "rules_evaluated": rules_applied,
        "compliance_controls": COMPLIANCE_FRAMEWORKS
    }

    payload["signature"] = sign_payload(payload, secret_key, allow_dev_fallback=allow_dev_fallback)
    return payload


def verify_receipt(
    receipt: Dict[str, Any],
    secret_key: Optional[bytes] = None,
    allow_dev_fallback: bool = False
) -> bool:
    """Verifies that an audit receipt has not been tampered with.

    Args:
        receipt: The audit receipt dictionary.
        secret_key: HMAC signing key.
        allow_dev_fallback: Whether to allow fallback to dev secret if key is missing.

    Returns:
        True if signature matches; False otherwise.
    """
    if "signature" not in receipt:
        return False

    provided_sig = receipt["signature"]
    payload_copy = {k: v for k, v in receipt.items() if k != "signature"}
    expected_sig = sign_payload(payload_copy, secret_key, allow_dev_fallback=allow_dev_fallback)

    return hmac.compare_digest(provided_sig, expected_sig)
