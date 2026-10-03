"""License management and local entitlement verification."""
import logging
import os

from yamlr.ui.theme import ICON_SUCCESS, console

logger = logging.getLogger(__name__)


EMBEDDED_PUBKEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAp4XtiV7KIfgUCt5Tvy4A
exuIYBqtKuy0Vbult2+p7sHinHGQM/dA2Vtd4GpGmojbzGNSekTTYleuOq/dZoKw
Cpcdwv2i8gPgbGU8DRHTXF8djLGSZQ3Sjko2CP+WRLRHz0aMNUe3jazvlE7DnH9C
lENzV1AjzUvCFyW/sdB31aPy53tMtcWat7haTz55tbw3TBi8MvsJ8tL3Ue0KmVS+
urVYOEGoljEWcURNJfmL6sBSuoWt27aGrEe+pKC/mjD+j2amIBPxVB8zKiZ1Q5yk
2cMxo1Am+tL0CkrzAAPzctiDdkAqtrIjeNN6tj+uK0ag42jeGPZqU86Bbp0cn8Zc
5wIDAQAB
-----END PUBLIC KEY-----"""


class LicenseManager:
    """Manages license verification, hardware fingerprints, and Pro features."""

    def __init__(self):
        self.is_pro = False
        self._mid = None
        self._load_entitlements()

    @property
    def mid(self) -> str:
        if not self._mid:
            self._mid = self._get_machine_id()
        return self._mid

    def _get_machine_id(self) -> str:
        """Retrieves the machine fingerprint from the Rust core."""
        try:
            import yamlr_native
            if hasattr(yamlr_native, "native_get_machine_id"):
                return yamlr_native.native_get_machine_id()
            return "mid-fallback"
        except ImportError:
            # Fallback for non-native environments: Stable Install-Bound UUID
            mid_path = os.path.expanduser("~/.yamlr/machine.id")
            if os.path.exists(mid_path):
                with open(mid_path, "r") as f:
                    return f.read().strip()

            import uuid
            mid = f"inst-{uuid.uuid4()}"
            os.makedirs(os.path.dirname(mid_path), exist_ok=True)
            with open(mid_path, "w") as f:
                f.write(mid)
            return mid

    def _get_pubkey(self) -> str:
        """Retrieves the public key for JWT verification.

        Why: Verification must work reliably whether running from a git checkout,
             a frozen PyInstaller executable, or an installed wheel package.
        """
        import sys
        candidates = []
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, "keys", "public_key.pem"))

        # 4 levels up: d:\yamlr\keys\public_key.pem (repository root)
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        candidates.append(os.path.join(repo_root, "keys", "public_key.pem"))
        # 3 levels up: d:\yamlr\src\keys\public_key.pem
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "keys", "public_key.pem"))
        # 2 levels up: d:\yamlr\src\yamlr\keys\public_key.pem
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "keys", "public_key.pem"))
        # Working directory fallback
        candidates.append(os.path.join(os.getcwd(), "keys", "public_key.pem"))

        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            return content
                except Exception as e:
                    logger.debug("Failed reading public key from %s: %s", path, e)
        return EMBEDDED_PUBKEY

    def _load_entitlements(self):
        """Loads and verifies local entitlements (Layered Storage)."""
        pubkey = self._get_pubkey()
        if self._load_from_env(pubkey): return
        self._load_from_keyring(pubkey)

    def _load_from_env(self, pubkey: str) -> bool:
        """Attempts to load token from environment variables."""
        import yamlr_native
        token = os.getenv("YAMLR_TOKEN")
        if token:
            if yamlr_native.native_verify_token(token, pubkey):
                self.is_pro = True
                return True
            console.print("[yellow][!] Environment token failed cryptographic verification.[/yellow]")
        return False

    def _load_from_keyring(self, pubkey: str) -> bool:
        """Attempts to load token from OS keyring."""
        import yamlr_native
        try:
            import keyring
            token = keyring.get_password("yamlr", "session_token")
            if token:
                if yamlr_native.native_verify_token(token, pubkey):
                    self.is_pro = True
                    return True
                keyring.delete_password("yamlr", "session_token")
        except (ImportError, OSError, RuntimeError) as e:
            logger.debug("Keyring access skipped or failed: %s", e)
        except Exception as e:
            logger.debug("Unexpected error loading token from keyring: %s", e)
        return False

    def check_pro(self) -> bool:
        """Dynamically verifies Pro status."""
        return self.is_pro

    def _save_token(self, token: str) -> bool:
        """Stores the token only in the operating system credential store."""
        try:
            import keyring
            keyring.set_password("yamlr", "session_token", token)
            return True
        except Exception as e:
            logger.debug("OS credential-store save failed: %s", e)
            return False

    def verify_token(self, token: str) -> bool:
        """Verifies a token against the offline public key."""
        import yamlr_native
        pubkey = self._get_pubkey()
        return yamlr_native.native_verify_token(token, pubkey)

    def activate_offline_key(self, key: str) -> bool:
        """Activates Yamlr Pro using an offline RSA-signed license key."""
        if self.verify_token(key):
            if not self._save_token(key):
                console.print("[bold red][!] Could not store the license in the OS credential store.[/bold red]")
                return False
            self.is_pro = True
            console.print(f"[bold green]{ICON_SUCCESS} Offline License Key activated successfully![/bold green]")
            return True
        else:
            console.print("[bold red][!] Invalid or expired license key.[/bold red]")
            return False
