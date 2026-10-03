#!/usr/bin/env python3
"""
Yamlr License Key Generator (Founder Tool)
------------------------------------------
Generates cryptographically signed license keys bound to a specific machine ID.

Usage:
  python generate_license_key.py <machine_id> [payload]

Example:
  python generate_license_key.py 123456789012 PRO-ANNUAL
"""

import hmac
import hashlib
import sys

def generate_key(machine_id: str, payload: str = "PRO-UNLIMITED") -> str:
    """
    Derives the machine-bound master key and signs the payload.
    
    Note: This MUST stay in sync with yamlr.pro.auth.AuthManager logic.
    """
    seed = machine_id.encode()
    
    # 1. Replicate PBKDF2 Master Key Derivation
    entropy = b"yamlr-ent-v2-" + seed
    salt = b"yamlr-salt-v2-" + hashlib.sha256(seed).digest()[:16]
    
    # [Engine Standard] 600k iterations ensures high cost of brute-forcing
    master_key = hashlib.pbkdf2_hmac("sha256", entropy, salt, 600000)
    
    # 2. Generate HMAC signature bound to the machine_id
    # We use the first 32 bytes of the master key as the secret
    sig = hmac.new(
        master_key[:32],
        f"{payload}:{machine_id}".encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    return f"YAMLR-{payload}-{sig}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_license_key.py <machine_id> [payload]")
        sys.exit(1)
    
    mid = sys.argv[1]
    p = sys.argv[2] if len(sys.argv) > 2 else "PRO-UNLIMITED"
    
    key = generate_key(mid, p)
    print(f"\n[Yamlr Founder Portal] Generated Secure Key:")
    print(f"-------------------------------------------")
    print(f"Machine ID: {mid}")
    print(f"Payload:    {p}")
    print(f"License Key: {key}")
    print(f"-------------------------------------------\n")
