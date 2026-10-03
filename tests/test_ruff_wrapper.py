"""Unit tests for the Ruff-model native binary discovery and execution wrapper.

Why: Ensures zero regression in binary resolution, subprocess forwarding,
     and fallback execution paths across operating systems.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yamlr._find_bin import find_yamlr_bin
from yamlr.__main__ import cli


def test_find_yamlr_bin_via_env_override(tmp_path, monkeypatch):
    """Test that YAMLR_BINARY environment variable takes top precedence."""
    bin_name = "yamlr.exe" if sys.platform == "win32" else "yamlr"
    mock_bin = tmp_path / bin_name
    mock_bin.write_text("#!/bin/sh\necho test", encoding="utf-8")
    mock_bin.chmod(0o755)

    monkeypatch.setenv("YAMLR_BINARY", str(mock_bin))
    discovered = find_yamlr_bin()
    assert discovered == str(mock_bin.resolve())


def test_find_yamlr_bin_finds_dev_target():
    """Test that find_yamlr_bin finds local target build if it exists."""
    bin_name = "yamlr.exe" if sys.platform == "win32" else "yamlr"
    repo_root = Path(__file__).resolve().parent.parent
    debug_bin = repo_root / "native_core" / "target" / "debug" / bin_name

    discovered = find_yamlr_bin()
    if debug_bin.is_file():
        assert discovered is not None
        assert Path(discovered).name.lower() == bin_name.lower()


def test_find_yamlr_bin_none_when_empty(monkeypatch):
    """Test find_yamlr_bin returns None when no candidates exist."""
    monkeypatch.setenv("YAMLR_BINARY", "/non/existent/path/yamlr")
    with patch("shutil.which", return_value=None), \
         patch("pathlib.Path.is_file", return_value=False):
        discovered = find_yamlr_bin()
        assert discovered is None


def test_cli_force_python_fallback(monkeypatch):
    """Test that YAMLR_FORCE_PYTHON=1 invokes the Python main entrypoint."""
    monkeypatch.setenv("YAMLR_FORCE_PYTHON", "1")
    with patch("yamlr.cli.main.main") as mock_py_main:
        cli()
        mock_py_main.assert_called_once()


def test_cli_dispatches_native_binary(monkeypatch):
    """Test that cli() forwards arguments to the native binary when found."""
    monkeypatch.delenv("YAMLR_FORCE_PYTHON", raising=False)
    fake_bin = "D:\\yamlr\\native_core\\target\\debug\\yamlr.exe"

    with patch("yamlr.__main__.find_yamlr_bin", return_value=fake_bin), \
         patch.object(sys, "argv", ["yamlr", "--version"]):
        if sys.platform == "win32":
            with patch("subprocess.call", return_value=0) as mock_call, \
                 patch("sys.exit") as mock_exit:
                cli()
                mock_call.assert_called_once_with([fake_bin, "--version"])
                mock_exit.assert_called_with(0)
        else:
            with patch("os.execv") as mock_execv:
                cli()
                mock_execv.assert_called_once_with(fake_bin, [fake_bin, "--version"])


def test_standalone_python_wrapper_package(monkeypatch):
    """Test standalone python_wrapper package discovery and invocation."""
    import importlib.util
    wrapper_path = Path(__file__).resolve().parent.parent / "python_wrapper" / "src" / "yamlr" / "__init__.py"
    assert wrapper_path.is_file(), "python_wrapper __init__.py must exist"

    spec = importlib.util.spec_from_file_location("yamlr_wrapper_pkg", str(wrapper_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with patch("shutil.which", return_value="/usr/local/bin/yamlr"), \
         patch("sys.exit") as mock_exit, \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        monkeypatch.setattr(sys, "argv", ["yamlr", "scan", "."])
        mod.main()
        mock_exit.assert_called_once_with(0)

