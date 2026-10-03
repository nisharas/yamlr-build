import json
import base64
import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

def issue_license(customer_name, tier="PRO", days=365):
    """Issues a signed Ed25519 license key for Yamlr Alpha."""
    
    # Generate an ephemeral key pair for the Alpha (in production, use a secure KMS)
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
    
    license_data = {
        "customer": customer_name,
        "tier": tier,
        "expiry": expiry,
        "issued_at": datetime.datetime.now().isoformat(),
        "version": "1.0"
    }
    
    # Sign the JSON payload
    payload = json.dumps(license_data, sort_keys=True).encode()
    signature = private_key.sign(payload)
    
    # Package into a single base64 string
    final_token = {
        "data": license_data,
        "signature": base64.b64encode(signature).decode()
    }
    
    token_b64 = base64.b64encode(json.dumps(final_token).encode()).decode()
    
    print("\n" + "="*60)
    print(f"   Yamlr Signed License Key Issued: {customer_name}")
    print("="*60)
    print(f"\nCUSTOMER:  {customer_name}")
    print(f"TIER:      {tier}")
    print(f"EXPIRY:    {expiry}")
    print(f"\n[KEY]:\n{token_b64}\n")
    print("="*60)
    
    # Save the public key for the engine to verify
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    with open("alpha_public_key.bin", "wb") as f:
        f.write(pub_bytes)
    
    print("\n[!] Public key saved to 'alpha_public_key.bin'.")
    print("[!] Ensure this key is embedded in the Yamlr binary for verification.")

if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "Early Adopter"
    issue_license(name)
