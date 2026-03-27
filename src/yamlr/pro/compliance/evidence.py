"""
Enterprise Evidence Engine
--------------------------
Generates DNA-signed JSON receipts for every auto-healed file.
Ensures cryptographic proof of what Yamlr altered for SOC2/HIPAA compliance pipelines.
"""

from __future__ import annotations
import os
import time
import json
import hmac
import hashlib
from pathlib import Path
from typing import Dict, Any, List
__all__ = ['EvidenceEngine']


class EvidenceEngine:
    """
    Computes cryptographic hashes of manifests before and after healing,
    and signs the resulting payload with a deterministic machine key.
    """
    
    KEY_PATH_RELATIVE = ".yamlr/evidence.key"

    def __init__(self):
        self._key = self._get_or_create_key()

    def _get_or_create_key(self) -> bytes:
        """Loads the evidence signing key from the user directory, or generates one securely."""
        key_file = Path.home() / self.KEY_PATH_RELATIVE
        if key_file.exists():
            return key_file.read_bytes()
        
        # Provision a new 256-bit cryptographically secure key
        key_file.parent.mkdir(parents=True, exist_ok=True)
        new_key = os.urandom(32)
        key_file.write_bytes(new_key)
        
        # Ensure strict permissions where supported (Unix-like)
        try:
            os.chmod(key_file, 0o600)
        except AttributeError:
            pass # Windows will silently skip chmod
            
        return new_key

    def _compute_sha256(self, content: str) -> str:
        """Returns the hex digest of the UTF-8 content."""
        if content is None:
            return ""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _sign_payload(self, payload_str: str) -> str:
        """Computes HMAC-SHA256 signature for the given payload."""
        return hmac.new(self._key, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()

    def generate_receipt(
        self, 
        file_path: str, 
        original_content: str, 
        healed_content: str, 
        findings: List[Dict[str, Any]],
        identities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates a self-contained, cryptographically signed JSON evidence receipt.
        """
        original_hash = self._compute_sha256(original_content)
        healed_hash = self._compute_sha256(healed_content)

        # 1. Construct the verifiable payload
        payload = {
            "file_path": file_path,
            "timestamp": time.time(),
            "original_sha256": original_hash,
            "healed_sha256": healed_hash,
            "identities": identities,
            "remediations": findings
        }

        # 2. Serialize deterministically to ensure stable hashing
        payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        
        # 3. Cryptographically sign the record
        signature = self._sign_payload(payload_str)
        
        # 4. Return the fully formed envelope
        receipt = {
            "signature_method": "HMAC-SHA256",
            "signature": signature,
            "payload": payload
        }
        
        return receipt

    def verify_receipt(self, receipt: Dict[str, Any]) -> bool:
        """
        Cryptographically verifies the authenticity of a receipt.
        """
        try:
            expected_signature = receipt["signature"]
            payload = receipt["payload"]
            # Serialize deterministically exactly as generated
            payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            actual_signature = self._sign_payload(payload_str)
            return hmac.compare_digest(expected_signature, actual_signature)
        except (json.JSONDecodeError, KeyError, AttributeError):
            return False
