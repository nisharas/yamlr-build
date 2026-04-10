"""
Yamlr A++: Platform-Specific Test Harness
-----------------------------------------
Validates OS-specific behaviors to ensure absolute portability.
Uses pytest.mark.skipif to selectively run tests on Windows vs Unix.
"""

import os
import signal
import sys
from pathlib import Path

import pytest

from yamlr.core.logging_config import mask_path

# --- CROSS-PLATFORM FIXTURES ---


@pytest.fixture
def mock_env(monkeypatch):
    """Clean environment for testing path masking."""
    monkeypatch.setenv("HOME", "/home/nisha")
    monkeypatch.setenv("USERPROFILE", "C:\\Users\\nisha")
    return monkeypatch


# --- WINDOWS SPECIFIC TESTS ---


@pytest.mark.skipif(sys.platform != "win32", reason="Windows path tests")
def test_windows_path_normalization():
    """Verify that backslashes are handled correctly in masking logic."""
    win_path = "C:\\Users\\nisha\\manifests\\pod.yaml"
    # Even on Windows, mask_path should normalize to ~ representation
    masked = mask_path(win_path)
    assert masked.startswith("~")
    assert "\\" not in masked or "Users" not in masked


@pytest.mark.skipif(sys.platform != "win32", reason="Windows environment tests")
def test_windows_userprofile_masking(monkeypatch):
    """Verify USERPROFILE is redacted on Windows."""
    up = "C:\\Users\\SecretUser"
    monkeypatch.setenv("USERPROFILE", up)
    monkeypatch.setattr(Path, "home", lambda: Path("C:/Users/SomeOtherHome"))

    # Force re-evaluation of sensitivity (mask_path uses os.environ)
    path = f"{up}\\Desktop\\config.yaml"
    masked = mask_path(path)
    assert up not in masked
    assert masked.startswith("~")


# --- UNIX SPECIFIC TESTS (Linux/macOS) ---


@pytest.mark.skipif(sys.platform == "win32", reason="Unix signal tests")
def test_unix_signal_handler_detection():
    """Verify signal handlers are registerable on Unix."""
    from yamlr.pro.opa_adapter import OpaAnalyzer

    analyzer = OpaAnalyzer(".")
    # This shouldn't raise ValueError on Unix
    analyzer._register_cleanup("/tmp/dummy")


@pytest.mark.skipif(sys.platform == "win32", reason="Unix filesystem tests")
def test_unix_root_masking():
    """Verify common Unix roots are not leaked if possible (future proofing)."""
    # Currently we only mask home/tmp/cwd, but we check if logic is robust
    tmp_path = "/tmp/yamlr-test-file.yaml"
    masked = mask_path(tmp_path)
    assert "/tmp/" not in masked
    assert masked.startswith("[TMP]")


# --- CROSS-PLATFORM LOGIC ---


def test_cwd_masking():
    """Verify CWD is masked as '.' across all platforms."""
    cwd = os.getcwd()
    path = os.path.join(cwd, "manifest.yaml")
    masked = mask_path(path)
    # On Windows CWD might be D:\yamlr, on Linux /home/user/yamlr
    assert masked.startswith(".") or masked == "."
    assert cwd[3:] not in masked  # Check that the tail of CWD is hidden
