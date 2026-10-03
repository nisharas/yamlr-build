"""Regression tests for Python fallback telemetry consent behavior."""

import json
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import pytest

cli_main = import_module("yamlr.cli.main")


class InteractiveInput:
    def isatty(self):
        return True


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("YAMLR_TELEMETRY", "0"),
        ("YAMLR_TELEMETRY", "false"),
        ("YAMLR_TELEMETRY", "off"),
        ("YAMLR_TELEMETRY", "no"),
        ("DO_NOT_TRACK", "1"),
        ("DO_NOT_TRACK", "true"),
    ],
)
def test_explicit_telemetry_opt_out_skips_prompt_and_local_write(
    monkeypatch, tmp_path, variable, value
):
    config_home = tmp_path / "home"
    monkeypatch.delenv("YAMLR_TELEMETRY", raising=False)
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.setenv(variable, value)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(sys, "stdin", InteractiveInput())
    monkeypatch.setattr(cli_main.os.path, "expanduser", lambda _: str(config_home))
    monkeypatch.setattr(cli_main.console, "input", lambda _: pytest.fail("telemetry prompt was shown"))

    cli_main._check_telemetry_optin()

    assert not config_home.exists()


@pytest.mark.parametrize("flag", ["--no-telemetry", "--disable-telemetry"])
def test_explicit_telemetry_flag_skips_prompt_and_local_write(monkeypatch, tmp_path, flag):
    config_home = tmp_path / "home"
    monkeypatch.delenv("YAMLR_TELEMETRY", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(sys, "stdin", InteractiveInput())
    monkeypatch.setattr(sys, "argv", ["yamlr", "scan", flag])
    monkeypatch.setattr(cli_main.os.path, "expanduser", lambda _: str(config_home))
    monkeypatch.setattr(cli_main.console, "input", lambda _: pytest.fail("telemetry prompt was shown"))

    cli_main._check_telemetry_optin()

    assert not config_home.exists()


def test_eof_from_consent_prompt_saves_opt_out_without_crashing(monkeypatch, tmp_path):
    config_home = tmp_path / "home"
    monkeypatch.delenv("YAMLR_TELEMETRY", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(sys, "stdin", InteractiveInput())
    monkeypatch.setattr(sys, "argv", ["yamlr", "scan"])
    monkeypatch.setattr(cli_main.os.path, "expanduser", lambda _: str(config_home))

    with patch.object(cli_main.console, "input", side_effect=EOFError):
        cli_main._check_telemetry_optin()

    preference = json.loads((config_home / "config.json").read_text(encoding="utf-8"))
    assert preference == {"telemetry_opt_in": False}
