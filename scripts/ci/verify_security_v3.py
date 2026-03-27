
import os
import json
import base64
import hashlib
from pathlib import Path
from yamlr.pro.auth import AuthManager

def test_credential_encryption():
    print("Testing Credential Encryption...")
    config_dir = Path("./.yamlr_test_creds")
    config_dir.mkdir(exist_ok=True)
    auth = AuthManager(app_name="YamlrTest", config_dir=config_dir)
    token = "test.token.sig"
    auth.save_credentials(token)
    
    # Check physical file content
    content = auth.creds_file.read_text()
    print(f"Physical file content: {content[:40]}...")
    
    # Verify it's NOT plaintext JSON
    try:
        json.loads(content)
        print("❌ FAILED: Credentials stored in plaintext!")
        return False
    except json.JSONDecodeError:
        print("✅ SUCCESS: Credentials are encrypted/obfuscated.")
        
    # Verify we can read it back
    read_token = auth.get_token()
    if read_token == token:
        print("✅ SUCCESS: Token correctly decrypted.")
    else:
        print(f"❌ FAILED: Decryption returned {read_token}")
        return False
        
    # Cleanup
    if auth.creds_file.exists(): auth.creds_file.unlink()
    return True

def test_env_scrubbing():
    print("\nTesting Env Var Scrubbing...")
    os.environ["Yamlr_LICENSE_KEY"] = "secret-env-token"
    auth = AuthManager()
    token = auth.get_token()
    if token == "secret-env-token" and "Yamlr_LICENSE_KEY" not in os.environ:
        print("✅ SUCCESS: Env var read and scrubbed.")
        return True
    print("❌ FAILED: Env var still exists or not read.")
    return False

if __name__ == "__main__":
    s1 = test_credential_encryption()
    s2 = test_env_scrubbing()
    if s1 and s2:
        print("\n🎉 ALL SECURITY TESTS PASSED (A+ PARITY)")
        exit(0)
    else:
        print("\n❌ SECURITY TESTS FAILED")
        exit(1)
