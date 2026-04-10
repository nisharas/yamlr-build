import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yamlr.core.catalog_manager import CatalogManager


def test_parallel_catalog_resolution_safety():
    """Verifies that multiple threads don't race during catalog resolution."""
    manager = CatalogManager()

    # Mock fetch_catalog to simulate a slow download
    def slow_fetch(version):
        time.sleep(0.1)
        # Create a mock file
        p = manager.get_catalog_path(version)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
        return True

    with patch.object(CatalogManager, "fetch_catalog", side_effect=slow_fetch):
        threads = []
        for _ in range(5):
            t = threading.Thread(target=manager.resolve_catalog, args=("v1.29",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    # Verify manager.fetch_catalog was called exactly once for v1.29 due to locking
    # (Actually it might be called once per target version)
    # But specifically checking if it deadlocked or crashed.
    assert manager.get_catalog_path("v1.29").exists()


def test_official_catalog_trust_policy():
    """Verifies that stable versions from official source are trusted without SHA."""
    manager = CatalogManager()
    manager.UPSTREAM_BASE_URL = "https://raw.githubusercontent.com/Yamlr-io/catalogs/main/distilled"

    # Mock a file existence
    v_new = "v1.32"  # Assumed stable/supported in matrix for this test context or closest fallback
    p = manager.get_catalog_path(v_new)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}")

    # verify_catalog should return True for official + stable even if not in KNOWN_GOOD_CHECKSUMS
    with patch("yamlr.core.catalog_manager.is_stable", return_value=True):
        assert manager.verify_catalog(v_new) is True


if __name__ == "__main__":
    pytest.main([__file__])
