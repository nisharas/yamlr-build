"""Verification Suite for Track 2.B: CLI Flag Progressive Disclosure.

Why: Empirically verifies that the Core 6 commands present structured, progressive
     argument groups to developers while preserving 100% flag backwards-compatibility,
     default values, and type invariance.
"""
import io
import json
from unittest.mock import patch

import pytest

from yamlr.cli.formatters import _render_global_help
from yamlr.cli.parser import create_parser


@pytest.fixture
def parser():
    """Build a fresh instance of the CLI argument parser."""
    return create_parser()


def _get_subparser(parser, name: str):
    """Retrieve child parser for a given subcommand name."""
    action = next(a for a in parser._actions if isinstance(getattr(a, "choices", None), dict))
    return action.choices[name]


def test_scan_help_argument_groups(parser):
    """Verify that 'yamlr scan --help' presents structured progressive argument groups."""
    scan_parser = _get_subparser(parser, "scan")

    help_out = io.StringIO()
    scan_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Options:" in output
    assert "Targeting & Environment:" in output
    assert "CI/CD & Pipeline Integration:" in output

    # Primary flags
    assert "--output" in output
    assert "-q, --quiet" in output
    assert "-w, --watch" in output

    # Targeting flags
    assert "--k8s-version" in output
    assert "--crd" in output
    assert "--helm" in output
    assert "--kustomize" in output

    # CI/CD flags
    assert "--fail-on" in output
    assert "-f, --output-file" in output
    assert "--exit-zero" in output
    assert "--push-telemetry" in output


def test_heal_help_argument_groups(parser):
    """Verify that 'yamlr heal --help' presents structured progressive argument groups."""
    heal_parser = _get_subparser(parser, "heal")

    help_out = io.StringIO()
    heal_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Remediation Options:" in output
    assert "Targeting & Environment:" in output
    assert "Policy & Tool Ingestion:" in output
    assert "CI/CD & Pipeline Integration:" in output

    # Primary remediation flags
    assert "--apply" in output
    assert "--diff" in output
    assert "--dry-run" in output

    # Policy ingestion flags
    assert "--ingest-opa" in output
    assert "--ingest-kyverno" in output


def test_diff_help_argument_groups(parser):
    """Verify that 'yamlr diff --help' presents structured progressive argument groups."""
    diff_parser = _get_subparser(parser, "diff")

    help_out = io.StringIO()
    diff_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Diff Options:" in output
    assert "Targeting & Environment:" in output
    assert "CI/CD & Pipeline Integration:" in output

    assert "-u, --unified" in output


def test_doctor_help_argument_groups(parser):
    """Verify that 'yamlr doctor --help' presents diagnostic argument groups."""
    doctor_parser = _get_subparser(parser, "doctor")

    help_out = io.StringIO()
    doctor_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Diagnostic Options:" in output
    assert "--fix" in output
    assert "Targeting & Environment:" in output


def test_scan_flag_parsing_invariance(parser):
    """Verify that all scan flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "scan", "manifests/deploy.yaml",
        "--output", "sarif",
        "-q",
        "-w",
        "--k8s-version", "1.31",
        "--crd", "crds/my-crd.yaml",
        "--helm",
        "--kustomize",
        "--fail-on", "error",
        "-f", "report.sarif",
        "--exit-zero",
        "--push-telemetry",
    ])

    assert args.command == "scan"
    assert args.path == "manifests/deploy.yaml"
    assert args.output == "sarif"
    assert args.quiet is True
    assert args.watch is True
    assert args.k8s_version == "1.31"
    assert args.crd == "crds/my-crd.yaml"
    assert args.helm is True
    assert args.kustomize is True
    assert args.fail_on == "error"
    assert args.output_file == "report.sarif"
    assert args.exit_zero is True
    assert args.push_telemetry is True


def test_heal_flag_parsing_invariance(parser):
    """Verify that all heal flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "heal", "manifests/",
        "--apply",
        "--diff",
        "--dry-run",
        "--ingest-opa", "gatekeeper.json",
        "--ingest-kyverno", "kyverno.json",
        "-f", "remediation.json",
        "--exit-zero",
        "--push-telemetry",
    ])

    assert args.command == "heal"
    assert args.path == "manifests/"
    assert args.apply is True
    assert args.diff is True
    assert args.dry_run is True
    assert args.ingest_opa == "gatekeeper.json"
    assert args.ingest_kyverno == "kyverno.json"
    assert args.output_file == "remediation.json"
    assert args.exit_zero is True
    assert args.push_telemetry is True


def test_diff_flag_parsing_invariance(parser):
    """Verify that all diff flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "diff", "manifests/service.yaml",
        "-u",
        "--helm",
        "--kustomize",
        "-f", "diff.sarif",
        "--exit-zero",
    ])

    assert args.command == "diff"
    assert args.path == "manifests/service.yaml"
    assert args.unified is True
    assert args.helm is True
    assert args.kustomize is True
    assert args.output_file == "diff.sarif"
    assert args.exit_zero is True


def test_core_6_rendered_count():
    """Verify that _render_global_help renders strictly 6 commands in Core."""
    with patch("yamlr.ui.renderer.RichRenderer.render_precision_help") as mock_render:
        _render_global_help(show_all=False)
        mock_render.assert_called_once()
        categories = mock_render.call_args[0][0]
        core_commands = categories["Basic Commands (Core)"]
        assert len(core_commands) == 6
        names = [cmd["name"] for cmd in core_commands]
        assert names == ["scan", "heal", "diff", "doctor", "status", "version"]


def test_status_help_argument_groups(parser):
    """Verify that 'yamlr status --help' presents structured progressive argument groups."""
    status_parser = _get_subparser(parser, "status")
    help_out = io.StringIO()
    status_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Options:" in output
    assert "--output" in output
    assert "CI/CD & Pipeline Integration:" in output
    assert "-f, --output-file" in output
    assert "--exit-zero" in output


def test_version_help_argument_groups(parser):
    """Verify that 'yamlr version --help' presents structured progressive argument groups."""
    version_parser = _get_subparser(parser, "version")
    help_out = io.StringIO()
    version_parser.print_help(help_out)
    output = help_out.getvalue()

    assert "Primary Options:" in output
    assert "--output" in output
    assert "CI/CD & Pipeline Integration:" in output
    assert "-f, --output-file" in output
    assert "--exit-zero" in output


def test_status_flag_parsing_invariance(parser):
    """Verify that status flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "status",
        "--output", "json",
        "-f", "status.json",
        "--exit-zero",
    ])
    assert args.command == "status"
    assert args.output == "json"
    assert args.output_file == "status.json"
    assert args.exit_zero is True


def test_version_flag_parsing_invariance(parser):
    """Verify that version flags parse with backwards-compatible names and types."""
    args = parser.parse_args([
        "version",
        "--output", "json",
        "-f", "version.json",
        "--exit-zero",
    ])
    assert args.command == "version"
    assert args.output == "json"
    assert args.output_file == "version.json"
    assert args.exit_zero is True


def test_status_json_execution(capsys):
    """Verify that cmd_status produces valid structured JSON when requested."""
    from yamlr.cli.handlers import cmd_status
    cmd_status(output="json")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["engine_version"] == "v0.1.0"
    assert data["status"] == "HEALTHY"
    assert "license" in data
    assert "machine_id" in data


def test_version_json_execution(capsys):
    """Verify that _cmd_version produces valid structured JSON when requested."""
    from yamlr.cli.handlers import _cmd_version
    _cmd_version(output="json")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "version" in data
    assert "native_core" in data
    assert "python" in data
