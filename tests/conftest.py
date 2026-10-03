import os
import shutil
import tempfile
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_workspace():
    """Provides a temporary workspace for file-based tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_native_core():
    """Mocks yamlr_native for logic-only tests."""
    mock = MagicMock()
    # Add default returns for common functions
    mock.native_get_build_info.return_value = {"version": "0.1.0", "build_id": "test"}
    mock.native_get_machine_id.return_value = "machine-test-123"
    return mock

@pytest.fixture
def signed_manifest(temp_workspace):
    """Creates a sample signed manifest for testing."""
    path = os.path.join(temp_workspace, "signed.yaml")
    content = """apiVersion: v1
kind: ConfigMap
metadata:
  name: test
  annotations:
    yamlr.dev/signature: "test-sig"
data:
  key: value
"""
    with open(path, 'w') as f:
        f.write(content)
    return path
