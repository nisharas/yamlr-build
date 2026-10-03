"""Regression tests for explicit offline-license signing-key configuration."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


GENERATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "founder"
    / "generate_offline_license.py"
)
SPEC = importlib.util.spec_from_file_location("generate_offline_license", GENERATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def test_founder_key_takes_precedence_over_legacy_key_name():
    key = GENERATOR._private_key_from_environment(
        {"YAMLR_FOUNDER_KEY": "founder-key", "YAMLR_PRIVATE_KEY": "legacy-key"}
    )

    assert key == "founder-key"


def test_legacy_key_environment_name_remains_supported():
    key = GENERATOR._private_key_from_environment({"YAMLR_PRIVATE_KEY": "legacy-key"})

    assert key == "legacy-key"


def test_missing_key_fails_before_creating_license_file(monkeypatch, tmp_path):
    monkeypatch.delenv("YAMLR_FOUNDER_KEY", raising=False)
    monkeypatch.delenv("YAMLR_PRIVATE_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="does not load signing keys from the repository"):
        GENERATOR.generate_license("", "developer@example.com", "team")

    assert not list(tmp_path.glob("license_*.jwt"))


def test_generation_uses_explicit_key_and_preserves_output(monkeypatch, tmp_path):
    signing = Mock(return_value="signed-token")
    monkeypatch.setattr(GENERATOR, "jwt", SimpleNamespace(encode=signing))
    monkeypatch.setenv("YAMLR_FOUNDER_KEY", "explicit-test-key")
    monkeypatch.chdir(tmp_path)

    GENERATOR.generate_license("", "developer@example.com", "team")

    signing.assert_called_once()
    assert signing.call_args.args[1] == "explicit-test-key"
    assert (tmp_path / "license_developer@example.com.jwt").read_text() == "signed-token"
