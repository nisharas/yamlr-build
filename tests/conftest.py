import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def ensure_runtime_dir():
    """Ensures .yamlr_runtime exists for all tests."""
    runtime_dir = Path(".yamlr_runtime")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def pytest_configure(config):
    """Global pytest configuration.

    Why: To ensure that any tests that write artifacts by default
         (without explicit path override) are encouraged to use
         the .yamlr_runtime directory.
    """
    # Force YAMLR_RUNTIME_DIR env var for tests
    os.environ["YAMLR_RUNTIME_DIR"] = ".yamlr_runtime"

    # We could also use this to monkeypatch any library that writes to root,
    # but for now, environment variable is the cleanest way.
