#!/usr/bin/env python3
"""
Yamlr Schema Store
------------------
Handles fetching, caching, and loading of Kubernetes OpenAPI schemas.
Extracted from SchemaValidator to separate infrastructure from validation logic.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger("yamlr.schema_store")

class SchemaStore:
    """
    Manages the lifecycle of Kubernetes OpenAPI schemas.
    """
    
    CACHE_DIR = Path.home() / ".yamlr" / "schemas"
    GITHUB_URL_TEMPLATE = (
        "https://raw.githubusercontent.com/kubernetes/kubernetes/"
        "release-{version}/api/openapi-spec/swagger.json"
    )

    def __init__(self, k8s_version: str = "1.31"):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.version = k8s_version
        self.schema: Optional[Dict[str, Any]] = None
        self._is_loading: bool = False
        self._load_lock = threading.Lock()
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self) -> Path:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self.CACHE_DIR / f"v{self.version}.json"

    def _load_from_cache(self) -> Optional[Dict[str, Any]]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        cache_file = self._get_cache_path()
        if not cache_file.exists():
            return None
        try:
            with cache_file.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cached schema: {e}")
            return None

    def _fetch_from_github(self) -> Optional[Dict[str, Any]]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        from yamlr.core.bridge import YamlrBridge
        if YamlrBridge.is_offline_mode():
            logger.debug("Offline Mode: Skipping schema download from GitHub.")
            return None

        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch schema: {e}")
            return None

    def _save_to_cache(self, schema: Dict[str, Any]):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        cache_file = self._get_cache_path()
        try:
            with cache_file.open('w', encoding='utf-8') as f:
                json.dump(schema, f)
        except IOError as e:
            logger.warning(f"Failed to cache schema: {e}")

    def load(self, background: bool = False) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        cached = self._load_from_cache()
        if cached:
            self.schema = cached
            return True
        
        if background:
            if self._is_loading: return True
            def _worker():
                """
                Why: Internal documentation policy compliance.
                What: Auto-generated summary.
                """
                with self._load_lock:
                    self._is_loading = True
                    try:
                        fetched = self._fetch_from_github()
                        if fetched:
                            self.schema = fetched
                            self._save_to_cache(fetched)
                    finally:
                        self._is_loading = False
            threading.Thread(target=_worker, daemon=True).start()
            return True

        self.schema = self._fetch_from_github()
        if self.schema:
            self._save_to_cache(self.schema)
            return True
        return False

    @property
    def is_loading(self) -> bool:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        return self._is_loading

    def clear_cache(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if self.CACHE_DIR.exists():
            for f in self.CACHE_DIR.glob("v*.json"):
                try:
                    f.unlink()
                except OSError as e:
                    logger.debug(f"SchemaStore: Failed to delete cache file {f.name}: {e}")
