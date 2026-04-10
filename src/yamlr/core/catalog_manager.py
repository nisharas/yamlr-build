"""
Yamlr CATALOG MANAGER
---------------------
Manages the lifecycle of Kubernetes schema definitions (catalogs).
Responsible for:
1.  Local storage (`~/.Yamlr/catalogs`)
2.  Fetching updates from upstream (Standard versions)
3.  Cache resolution
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from yamlr.core.entrypoints.base import get_console
from yamlr.core.k8s_versions import MATRIX, closest_supported, is_stable, is_supported

logger = logging.getLogger("yamlr.catalog")

__all__ = ["CatalogManager"]


class CatalogManager:
    """
    Manages versioned Kubernetes catalogs (distilled schemas).
    """

    # Placeholder for the official Yamlr schema repository
    # [Hardening] Detect test environment to prevent production URL leaks
    _is_test = "PYTEST_CURRENT_TEST" in os.environ or "YAMLR_TEST" in os.environ

    UPSTREAM_BASE_URL = os.getenv(
        "Yamlr_CATALOG_URL",
        "http://localhost:9999/mock-catalogs"
        if _is_test
        else "https://raw.githubusercontent.com/Yamlr-io/catalogs/main/distilled",
    )

    # Path to bundled catalogs within the package
    BUNDLED_DIR = Path(__file__).parent.parent / "catalog"

    # Map of known good checksums for bundled catalogs.
    # Key: Normalized version (e.g., "v1"), Value: SHA256 checksum
    KNOWN_GOOD_CHECKSUMS = {
        "v1.31": "e0bcf3ee514c1daf090118921c681c9085105c66e91147443ed7258cf152adc1d",
        "minimal": "6bd6d639a69912b576d910f7e240222082d735a1dcaab2f8de65ce0bc2edfa0f",
    }

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Args:
            storage_dir: Custom path for catalog storage.
                         Defaults to ~/.Yamlr/catalogs
        """
        self._custom_storage = storage_dir
        self._storage_dir: Optional[Path] = None
        self._parsed_cache: Dict[str, Dict[str, Any]] = {}  # [PHASE-11] In-memory catalog cache
        # [ROUND-10] Sticky Redirection Cache: Prevents redundant adaptation penalties
        self._adaptation_cache: Dict[str, str] = {}
        self._lock = threading.Lock()  # [ROUND-7] Thread-safety for parallel workers

    @property
    def storage_dir(self) -> Path:
        """Lazy-loaded storage directory path."""
        if self._storage_dir is None:
            if self._custom_storage:
                self._storage_dir = Path(self._custom_storage).resolve()
            else:
                env_path = os.getenv("Yamlr_CATALOG_PATH")
                if env_path:
                    self._storage_dir = Path(env_path).resolve()
                else:
                    self._storage_dir = Path.home() / ".yamlr" / "catalogs"
        return self._storage_dir

    def _ensure_storage(self):
        """Ensures the local catalog storage directory exists.

        Why: Deferring this until first write saves ~20-50ms on startup.
        """
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create catalog storage: {e}")

    def get_catalog_path(self, version: str, bundled: bool = False) -> Path:
        """
        Constructs the expected path for a version.

        Args:
            version: Normalized version string.
            bundled: If True, returns the path in the package assets.
        """
        version = self._normalize_version(version)
        base = self.BUNDLED_DIR if bundled else self.storage_dir
        return base / f"k8s_{version}_distilled.json"

    def resolve_catalog(self, version: str, intent: str = "analysis", auto_fetch: bool = True) -> str:
        """
        Intelligent resolution of catalog path with thread-safety.

        Why: Ensures that parallel workers do not attempt to download the
             same catalog simultaneously, preventing file corruption.
        """
        with self._lock:
            # 0. Check Adaptation Cache [ROUND-10 Sticky Redirection]
            if version in self._adaptation_cache:
                redirected_v = self._adaptation_cache[version]
                return self._resolve_catalog_unlocked(redirected_v, intent, auto_fetch)

            return self._resolve_catalog_unlocked(version, intent, auto_fetch)

    def _resolve_catalog_unlocked(self, version: str, intent: str, auto_fetch: bool) -> str:
        """Internal helper for resolve_catalog to avoid deadlocks with threading.Lock."""
        console = get_console()

        # 1. Check Local Cache
        cached_path = self.get_catalog_path(version)
        if cached_path.exists():
            return str(cached_path)

        # 2. Check Bundled Assets
        bundled_path = self.get_catalog_path(version, bundled=True)
        if bundled_path.exists():
            return str(bundled_path)

        # 3. Dynamic Acquisition (Stable-Only)
        if auto_fetch and is_stable(version):
            # Check if this version is NOT the default to explain WHY we are downloading
            if version != f"v{MATRIX.default_recommended}":
                console.print(
                    f"[bold cyan]◌[/bold cyan] K8s {version} is not the default version (v{MATRIX.default_recommended})."
                )
                console.print(
                    f"[bold cyan]◌[/bold cyan] Attempting to download high-fidelity {version} catalog for {intent}..."
                )

            if self.fetch_catalog(version) and cached_path.exists():
                console.print(
                    f"[bold green]✔[/bold green] {version} catalog acquired. Proceeding with native intelligence."
                )
                return str(cached_path)

        # 4. Adaptive Fallback
        closest = closest_supported(version)
        self._adaptation_cache[version] = closest

        console.print(f"[bold yellow]⚠[/bold yellow] High-fidelity catalog for {version} is unavailable.")
        console.print(f"  Switching to [green]Adaptive Compatibility Mode[/green] using the v{closest} stable base.")

        closest_cached = self.get_catalog_path(closest)
        if closest_cached.exists():
            return str(closest_cached)

        closest_bundled = self.get_catalog_path(closest, bundled=True)
        if closest_bundled.exists():
            return str(closest_bundled)

        return str(cached_path)

    def get_catalog_data(self, version: str) -> Dict[str, Any]:
        """
        Retrieves the parsed JSON catalog for a version, using in-memory cache.
        """
        # [ROUND-11] Version is already normalized by get_catalog_path inside resolve_catalog
        with self._lock:
            if version not in self._parsed_cache:
                path_str = self._resolve_catalog_unlocked(version, intent="data-loading", auto_fetch=True)
                path = Path(path_str)
                if path.exists():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            self._parsed_cache[version] = json.load(f)
                    except (json.JSONDecodeError, OSError) as e:
                        logger.error(f"Catalog: Corrupted or unreadable file {path}: {e}")
                        try:
                            path.unlink()
                            logger.warning(f"Catalog: Purged corrupted {path.name}")
                        except OSError:
                            pass
                        return {}
                else:
                    return {}
            return self._parsed_cache[version]

    def fetch_catalog(self, version: str) -> bool:
        """
        Downloads and installs the specified version's catalog from upstream.
        Returns True if successful.
        """
        version = self._normalize_version(version)
        target_path = self.get_catalog_path(version)
        url = f"{self.UPSTREAM_BASE_URL}/k8s_{version}_distilled.json"

        data = self._download_bytes(url)
        if not data:
            return False

        return self._validate_and_save(data, target_path, version)

    def _download_bytes(self, url: str) -> Optional[bytes]:
        """Handles the low-level HTTPS request and retries.

        Why: Decomposed to satisfy cognitive complexity limits and ensure
             secure protocol defaults.
        """
        if not url.startswith("https://"):
            logger.error(f"Catalog: Refusing non-HTTPS URL: {url}")
            return None

        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = self._execute_download(url)
                if data is not None:
                    return data
            except (urllib.error.URLError, ConnectionError) as e:
                if self._handle_download_error(e, attempt, max_retries):
                    continue
                return None
        return None

    def _execute_download(self, url: str) -> Optional[bytes]:
        """Executes a single download request with secure defaults."""
        headers = {"User-Agent": "Yamlr-CLI/0.1.0"}
        req = urllib.request.Request(url, headers=headers)

        # [Security] Use default context with explicit minimum TLS 1.2 to satisfy linters.
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        try:
            with urllib.request.urlopen(req, timeout=10, context=context) as response:
                if response.status == 200:
                    return response.read()
                return None
        except urllib.error.HTTPError as e:
            logger.debug(f"Catalog: HTTP Error {e.code} for {url}")
            return None

    def _handle_download_error(self, error: Exception, attempt: int, max_retries: int) -> bool:
        """Determines if a download error is retryable and performs delay."""
        err_str = str(error).lower()
        # [Hardening] Zero-Blindspot: Check if error is fatal
        fatal_markers = ["getaddrinfo", "refused", "name or service not known", "forbidden", "unauthorized"]
        is_fatal = any(x in err_str for x in fatal_markers)

        if is_fatal:
            logger.error(f"Upstream network failure (fatal): {error}")
            return False

        if attempt < max_retries - 1:
            retry_delay = 1.0 * (attempt + 1)
            time.sleep(retry_delay)
            return True

        logger.error(f"Upstream network failure (exhausted): {error}")
        return False

    def _validate_and_save(self, data: bytes, target_path: Path, version: str) -> bool:
        """Handles JSON validation, atomic storage, and checksum verification."""
        try:
            content = json.loads(data)
            if not isinstance(content, dict):
                logger.error("Invalid catalog format: Root is not a dict.")
                return False
        except json.JSONDecodeError:
            logger.error("Failed to parse catalog JSON from upstream.")
            return False

        # [ROUND-9] Forensic Audit: Log payload DNA before storage
        payload_sha = hashlib.sha256(data).hexdigest()
        logger.info(f"Catalog: Received payload for {version} [SHA256: {payload_sha[:12]}...]")

        # Atomic Write
        self._ensure_storage()
        temp_path = target_path.with_suffix(f".tmp.{uuid.uuid4().hex}")
        try:
            temp_path.write_bytes(data)
            os.replace(temp_path, target_path)

            # [ROUND-8] Invalidate in-memory cache on update to prevent stale data
            with self._lock:
                self._parsed_cache.pop(version, None)

        except (OSError, IOError) as e:
            logger.error(f"Failed to write catalog to disk: {e}")
            return False

        # Post-install Verification
        if not self.verify_catalog(version):
            logger.error(f"Catalog {version} failed integrity verification! Purging local copy.")
            if target_path.exists():
                target_path.unlink()
            return False

        logger.info(f"Successfully installed catalog for {version}")
        return True

    def list_installed_versions(self) -> List[str]:
        """Returns list of locally available versions (e.g. ['v1.28', 'v1.29'])."""
        if not self.storage_dir.exists():
            return []

        versions = []
        for f in self.storage_dir.glob("k8s_*_distilled.json"):
            # Extract version from filename "k8s_v1.28_distilled.json"
            try:
                name = f.name
                if name.startswith("k8s_") and name.endswith("_distilled.json"):
                    ver = name[4:-15]
                    versions.append(ver)
            except (ValueError, IndexError):
                continue
        return sorted(versions)

    def prune(self, days: int = 30):
        """Removes old cached catalogs that haven't been accessed for a while.

        Why: To satisfy M&A readiness by ensuring the local binary footprint
             remains optimized over long-term usage.
        """
        now = time.time()
        cutoff = now - (days * 86400)

        count = 0
        if not self.storage_dir.exists():
            return 0

        for f in self.storage_dir.glob("k8s_v*_distilled.json"):
            if f.stat().st_mtime < cutoff:
                try:
                    f.unlink()
                    count += 1
                    logger.info(f"Catalog: Pruned old cached version {f.name}")
                except OSError as e:
                    logger.warning(f"Catalog: Failed to prune {f.name}: {e}")

        # [ROUND-9] Ghost Cleanup: Purge orphaned temporary files
        for tmp_f in self.storage_dir.glob("*.tmp.*"):
            if tmp_f.stat().st_mtime < cutoff:
                try:
                    tmp_f.unlink()
                    logger.info(f"Catalog: Cleaned up orphaned temporary file {tmp_f.name}")
                except OSError:
                    pass

        return count

    def sync_all(self, console: Optional[Any] = None) -> List[str]:
        """
        Batch-downloads all stable catalogs defined in the support matrix.

        Why: To enable "Air-Gap Pre-warming" (Tier 1 Habit), ensuring all
             supported versions are available offline.
        """
        synced = []
        stable_versions = [f"v{v}" for v in MATRIX.supported_versions]

        if console:
            console.print(f"[bold cyan]◌[/bold cyan] Syncing Kubernetes Matrix ({len(stable_versions)} versions)...")

        for v in stable_versions:
            path = self.get_catalog_path(v)
            if path.exists():
                logger.debug(f"Catalog: {v} already cached.")
                continue

            if self.fetch_catalog(v):
                synced.append(v)
                if console:
                    console.print(f"  [green]✔[/green] {v} synchronized.")
            else:
                if console:
                    console.print(f"  [red]✘[/red] {v} failed.")

        return synced

    def verify_catalog(self, version: str) -> bool:
        """
        Verifies the integrity of a locally stored catalog file using SHA256.
        Returns True if valid or if no checksum is registered for the version.
        """
        version = self._normalize_version(version)
        path = self.get_catalog_path(version)
        if not path.exists():
            return False

        expected_sha = self.KNOWN_GOOD_CHECKSUMS.get(version)
        if not expected_sha:
            # [ROUND-11] Refined Policy: Allow official stable catalogs even if SHA not hardcoded.
            # This ensures zero-friction for future K8s versions without code updates.
            if str(self.BUNDLED_DIR) in str(path):
                return True  # Bundled assets are always trusted

            is_official = self.UPSTREAM_BASE_URL.startswith("https://raw.githubusercontent.com/Yamlr-io/")
            is_current_stable = is_supported(version) or is_stable(version)

            if is_official and is_current_stable:
                logger.info(f"Integrity: Trusting official stable catalog for {version} (Opt-in via official SSOT).")
                return True

            if os.getenv("YAMLR_ALLOW_UNVERIFIED_CATALOG") == "1":
                logger.warning(f"Integrity Warning: No registered checksum for {version}. Proceeding via opt-in trust.")
                return True

            logger.error(f"Integrity Error: No registered checksum for {version}. Refusing unverified download.")
            logger.info("To allow unverified catalogs, set YAMLR_ALLOW_UNVERIFIED_CATALOG=1")
            return False

        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        actual_sha = sha256_hash.hexdigest()
        if actual_sha != expected_sha:
            logger.error(f"Integrity check failed for {version}!")
            logger.error(f"Expected: {expected_sha}")
            logger.error(f"Actual:   {actual_sha}")
            return False

        return True

    def _normalize_version(self, version: Optional[str]) -> str:
        """Ensures 'vX.Y' format while allowing patch-pinning in resolve_catalog."""
        if not version:
            return f"v{MATRIX.default_recommended}"

        # [ROUND-10] Support Patch-level pinning if provided exactly
        v_str = str(version).strip().lower().lstrip("v")
        if re.match(r"^\d+\.\d+\.\d+$", v_str):
            return f"v{v_str}"

        from yamlr.core.k8s_versions import normalize_version

        return normalize_version(version)
