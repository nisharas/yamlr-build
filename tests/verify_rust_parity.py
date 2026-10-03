#!/usr/bin/env python3
"""Compare the supported Python CLI bridge with the standalone Rust CLI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_BRIDGE = (
    "import sys; import yamlr.__main__ as entry; "
    "entry.find_yamlr_bin = lambda: None; "
    "sys.argv = ['yamlr', *sys.argv[1:]]; entry.cli()"
)
TIMING_FIELDS = {"duration_ms", "elapsed_ms", "total_time_ms"}
CASE_COUNT = 0
SUPPORTED_COMMANDS = [
    "scan",
    "lint",
    "heal",
    "check",
    "diff",
    "schema",
    "explain",
    "audit",
    "catalog",
    "baseline",
    "fmt",
    "fix",
    "legal",
    "manual",
    "man",
    "migrate",
    "rules",
    "welcome",
    "features",
    "status",
    "demo",
    "lsp",
    "mcp",
    "install",
    "doctor",
    "diagnose",
    "version",
    "help",
    "completion",
    "guide",
    "init",
    "dna",
    "sign",
    "verify",
    "graph",
    "drift",
    "rollback",
    "restore",
    "roi",
    "impact",
    "pulse",
    "metrics",
    "stats",
    "secure",
    "evidence",
    "idp-export",
    "watch",
    "fleet",
    "webhook",
    "rpc",
    "service",
    "daemon",
    "subscribe",
    "upgrade",
    "auth",
    "admin",
    "vap",
    "export-vap",
    "--version",
    "-v",
    "--help",
    "-h",
]


def run(command: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: normalize(item)
            for key, item in value.items()
            if key not in TIMING_FIELDS
        }
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def compare_case(
    name: str,
    args: list[str],
    native_bin: Path,
    env: dict[str, str],
    *,
    report: Path | None = None,
    expect_success: bool = True,
    expected_exit: int | None = None,
) -> None:
    global CASE_COUNT
    CASE_COUNT += 1
    native_report = report.with_name("native.json") if report else None
    python_report = report.with_name("python.json") if report else None

    def with_report_path(report_path: Path | None) -> list[str]:
        return [
            str(report_path) if arg == "__REPORT__" and report_path else arg
            for arg in args
        ]

    native_args = [str(native_bin), *with_report_path(native_report)]
    python_args = [
        sys.executable,
        "-I",
        "-c",
        PYTHON_BRIDGE,
        *with_report_path(python_report),
    ]
    native = run(native_args, env=env)
    python = run(python_args, env=env)

    for label, result in (("Rust binary", native), ("Python bridge", python)):
        if result.returncode < 0:
            raise SystemExit(
                f"{name}: {label} terminated by signal {-result.returncode}"
            )

    if native.returncode != python.returncode:
        raise SystemExit(
            f"{name}: exit-code mismatch: Rust={native.returncode}, "
            f"Python={python.returncode}\nRust stderr:\n{native.stderr}\n"
            f"Python stderr:\n{python.stderr}"
        )
    if (native.returncode == 0) != expect_success:
        expected = "success" if expect_success else "a nonzero exit code"
        raise SystemExit(f"{name}: expected {expected}, got {native.returncode}")
    if expected_exit is not None and native.returncode != expected_exit:
        raise SystemExit(
            f"{name}: expected exit {expected_exit}, got {native.returncode}"
        )

    native_stderr = native.stderr
    python_stderr = python.stderr
    if native_report and python_report:
        native_stderr = native_stderr.replace(str(native_report), "<REPORT>")
        python_stderr = python_stderr.replace(str(python_report), "<REPORT>")
    if native_stderr != python_stderr:
        raise SystemExit(
            f"{name}: stderr mismatch\nRust:\n{native_stderr}\nPython:\n{python_stderr}"
        )

    if report is not None:
        reports = []
        for label, report_path in (
            ("Rust", native_report),
            ("Python", python_report),
        ):
            assert report_path is not None
            if not report_path.is_file():
                raise SystemExit(f"{name}: {label} CLI did not write its JSON report")
            try:
                parsed = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise SystemExit(
                    f"{name}: invalid {label} JSON report: {error}"
                ) from error
            import jsonschema

            contract = json.loads(
                (REPO_ROOT / "schemas" / "scan-report.schema.json").read_text(
                    encoding="utf-8"
                )
            )
            jsonschema.Draft202012Validator(contract).validate(parsed)
            if not isinstance(parsed, dict) or (
                parsed.get("status") != "error"
                and not isinstance(parsed.get("results"), list)
            ):
                raise SystemExit(
                    f"{name}: report is missing the shared results structure"
                )
            reports.append(normalize(parsed))
        if reports[0] != reports[1]:
            raise SystemExit(
                f"{name}: JSON report mismatch\nRust: {reports[0]}\nPython: {reports[1]}"
            )

        assert native_report is not None and python_report is not None
        normalized_native_stdout = native.stdout.replace(str(native_report), "<REPORT>")
        normalized_python_stdout = python.stdout.replace(str(python_report), "<REPORT>")
        if normalized_native_stdout != normalized_python_stdout:
            raise SystemExit(f"{name}: stdout mismatch after report-path normalization")
        return

    if args == ["version", "--json"]:
        try:
            native_output = json.loads(native.stdout)
            python_output = json.loads(python.stdout)
        except json.JSONDecodeError as error:
            raise SystemExit(f"version --json did not produce JSON: {error}") from error
        if normalize(native_output) != normalize(python_output):
            raise SystemExit("version --json output mismatch between Rust and Python")
    elif native.stdout != python.stdout:
        native_stdout = native.stdout
        python_stdout = python.stdout
        if args and args[0] == "sign":
            import re
            native_stdout = re.sub(r'yamlr\.dev/signed-at:\s*".*?"', 'yamlr.dev/signed-at: "<NORMALIZED>"', native_stdout)
            python_stdout = re.sub(r'yamlr\.dev/signed-at:\s*".*?"', 'yamlr.dev/signed-at: "<NORMALIZED>"', python_stdout)
            native_stdout = re.sub(r'yamlr\.dev/signature:\s*".*?"', 'yamlr.dev/signature: "<NORMALIZED>"', native_stdout)
            python_stdout = re.sub(r'yamlr\.dev/signature:\s*".*?"', 'yamlr.dev/signature: "<NORMALIZED>"', python_stdout)
        if native_stdout != python_stdout:
            raise SystemExit(
                f"{name}: stdout mismatch\nRust:\n{native.stdout}\nPython:\n{python.stdout}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-bin", required=True, type=Path)
    args = parser.parse_args()
    native_bin = args.native_bin.resolve()
    if not native_bin.is_file():
        raise SystemExit(f"Rust CLI binary not found: {native_bin}")

    env = os.environ.copy()
    env["YAMLR_TELEMETRY"] = "off"
    env["CI"] = "true"
    env.pop("YAMLR_FORCE_PYTHON", None)
    env.pop("YAMLR_BINARY", None)

    private_key_path = REPO_ROOT / "native_core" / "tests" / "fixtures" / "licensing_test_private.pem"
    public_key_path = REPO_ROOT / "native_core" / "tests" / "fixtures" / "licensing_test_public.pem"
    if private_key_path.is_file() and public_key_path.is_file():
        import time, jwt
        now = int(time.time())
        claims = {
            "license_version": 1,
            "sub": "org_enterprise_test",
            "org_id": "org_enterprise_test",
            "iat": now,
            "exp": now + 86400 * 365,
            "tier": "enterprise",
            "iss": "yamlr-entitlement",
            "aud": "yamlr",
            "seats": 500,
            "org_seats": 500,
        }
        test_token = jwt.encode(claims, private_key_path.read_text(encoding="utf-8"), algorithm="RS256")
        env["YAMLR_LICENSE_PUBLIC_KEY"] = str(public_key_path.resolve())
        env["YAMLR_LICENSE_TOKEN"] = test_token

    with tempfile.TemporaryDirectory(prefix="yamlr-cli-parity-") as directory:
        temp_dir = Path(directory)
        manifest = temp_dir / "pod.yaml"
        manifest.write_text(
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n"
            "  name: parity-smoke\n"
            "spec:\n"
            "  containers:\n"
            "    - name: app\n"
            "      image: nginx:latest\n",
            encoding="utf-8",
        )

        report = temp_dir / "scan-report.json"
        for index, constraint in enumerate(
            ("minimum: 1", "enum: [1, 2]", "nullable: true")
        ):
            crd = temp_dir / f"unsupported-{index}.yaml"
            crd.write_text(
                "apiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\n"
                "metadata:\n  name: widgets.example.test\nspec:\n  group: example.test\n"
                "  names:\n    kind: Widget\n  versions:\n    - name: v1\n"
                "      schema:\n        openAPIV3Schema:\n          type: object\n"
                "          properties:\n            spec:\n              type: string\n"
                f"              {constraint}\n",
                encoding="utf-8",
            )
            compare_case(
                f"unsupported CRD constraint {index}",
                [
                    "scan",
                    str(manifest),
                    "--crd",
                    str(crd),
                    "--output",
                    "json",
                    "--output-file",
                    "__REPORT__",
                    "--exit-zero",
                ],
                native_bin,
                env,
                report=report,
                expect_success=False,
                expected_exit=2,
            )
        compare_case(
            "scan JSON report",
            [
                "scan",
                str(manifest),
                "--output",
                "json",
                "--output-file",
                "__REPORT__",
                "--exit-zero",
            ],
            native_bin,
            env,
            report=report,
        )
        compare_case("version JSON", ["version", "--json"], native_bin, env)
        compare_case(
            "unsupported output format",
            ["scan", str(manifest), "--output", "xml"],
            native_bin,
            env,
            expect_success=False,
        )
        compare_case(
            "unknown scan option",
            ["scan", str(manifest), "--parity-unknown-option"],
            native_bin,
            env,
            expect_success=False,
        )

        extra_cases = []
        for command in SUPPORTED_COMMANDS:
            extra_cases.append((f"{command} help", [command, "--help"], True))
            extra_cases.append(
                (
                    f"{command} unknown option",
                    [command, "--parity-unknown-option"],
                    False,
                )
            )
        for tail in [
            ["--output"],
            ["--k8s-version"],
            ["--output=json", "--output=text"],
            ["--k8s-version=1.30", "--kube-version=1.30"],
            ["--fail-on=unknown"],
            ["--k8s-version=invalid"],
            ["--output=admission-review"],
            ["--json", "--sarif"],
            ["--json", "--output=json"],
            ["--helm", "--kustomize"],
        ]:
            extra_cases.append(
                (f"scan rejects {tail}", ["scan", str(manifest), *tail], False)
            )
        for name, tail, success in extra_cases:
            compare_case(
                name,
                tail,
                native_bin,
                env,
                expect_success=success,
                expected_exit=3 if name.endswith("unknown option") else None,
            )
        for command, tail in [
            ("audit", ["--output"]),
            ("audit", ["--output=xml"]),
            ("catalog", ["--category="]),
            ("catalog", ["-j", "--json"]),
            ("baseline", ["--create", "--check"]),
            ("baseline", ["--file"]),
            ("fmt", ["-w", "--write"]),
            ("fix", ["--apply", "-a"]),
            ("install", ["--git-hook", "-g"]),
            ("version", ["--json", "-j"]),
            ("doctor", ["--verbose", "-v"]),
            ("init", ["--force", "-f"]),
            ("dna", ["--json", "-j"]),
            ("completion", ["bash", "zsh"]),
            ("completion", ["unsupported-shell"]),
            ("guide", ["security", "network"]),
            ("lsp", ["unexpected-path"]),
            ("mcp", ["unexpected-path"]),
            ("sign", ["--key"]),
            ("sign", ["--write", "--in-place"]),
            ("verify", ["--key="]),
            ("graph", ["--focus"]),
            ("drift", ["one", "two"]),
            ("rollback", ["--list", "transaction"]),
            ("restore", ["--journal"]),
            ("metrics", ["--output=xml"]),
            ("roi", ["--output"]),
            ("secure", ["--output="]),
            ("idp-export", ["--format=unknown"]),
            ("evidence", ["-j", "--json"]),
            ("fleet", ["--k8s-version=invalid"]),
            ("fleet", ["--apply", "-a"]),
            ("webhook", ["--port=0"]),
            ("webhook", ["--port=65536"]),
            ("webhook", ["--dry-run", "--dry-run"]),
            ("rpc", ["--port=invalid"]),
            ("service", ["--port"]),
            ("daemon", ["--test", "--dry-run"]),
            ("auth", ["activate"]),
            ("auth", ["status", "--key=unused"]),
            ("auth", ["activate", "test-only-token", "--key=unused"]),
            ("admin", ["config-reset", "--unknown"]),
            ("vap", ["ingest"]),
            ("vap", ["export", "policy.yaml"]),
            ("vap", ["ingest", "policy.yaml", "--output=unused"]),
            ("vap", ["--ingest", "--file=unused", "--name=unused"]),
        ]:
            compare_case(
                f"{command} rejects {tail}",
                [command, *tail],
                native_bin,
                env,
                expect_success=False,
            )
        compare_case(
            "compact catalog category", ["catalog", "-csecurity"], native_bin, env
        )
        compare_case("shell completion", ["completion", "bash"], native_bin, env)
        compare_case("guide topic", ["guide", "--", "security"], native_bin, env)
        compare_case("DNA JSON", ["dna", "-j", "--", str(manifest)], native_bin, env)
        compare_case(
            "metrics compact JSON",
            ["metrics", "-ojson", "--", str(manifest)],
            native_bin,
            env,
        )
        sign_args = ["sign", "--key=test-only-signing-value", "--", str(manifest)]
        sign_probe = run([str(native_bin), *sign_args], env=env)
        sign_denied = (
            sign_probe.returncode == 1 and "requires the paid tier" in sign_probe.stderr
        )
        if sign_probe.returncode != 0 and not sign_denied:
            raise SystemExit(f"Unexpected signing failure: {sign_probe.stderr}")
        compare_case(
            "sign preview or entitlement denial",
            sign_args,
            native_bin,
            env,
            expect_success=not sign_denied,
        )
        if sign_denied:
            print(
                "Paid signing parity verified at the entitlement gate; execution needs a test entitlement."
            )
        else:
            print(
                "Paid signing executable parity verified across Rust and Python under test entitlement."
            )
        compare_case(
            "graph compact focus",
            ["graph", "-fparity", "--", str(manifest)],
            native_bin,
            env,
        )
        compare_case(
            "webhook configuration",
            ["webhook", "--dry-run", "--port=9443"],
            native_bin,
            env,
        )
        compare_case("RPC configuration", ["rpc", "-p50052", "--test"], native_bin, env)
        compare_case(
            "RPC unsupported listener", ["rpc"], native_bin, env, expect_success=False
        )
        compare_case(
            "initializer rejects before writing",
            ["init", str(temp_dir), "--parity-unknown-option"],
            native_bin,
            env,
            expect_success=False,
        )
        if (temp_dir / ".yamlr.yaml").exists():
            raise SystemExit("invalid initializer arguments wrote a configuration")
        original = manifest.read_bytes()
        compare_case("formatter preview", ["fmt", "--", str(manifest)], native_bin, env)
        if manifest.read_bytes() != original:
            raise SystemExit("formatter preview changed its input manifest")
        compare_case(
            "compact scan report options",
            [
                "scan",
                "-ojson",
                "--kube-version=1.30",
                "--output-file",
                "__REPORT__",
                "--exit-zero",
                "--",
                str(manifest),
            ],
            native_bin,
            env,
            report=report,
        )

        unreadable = temp_dir / "invalid-encoding.yaml"
        unreadable.write_bytes(b"\xff\xfe")
        compare_case(
            "incomplete scan error report despite exit-zero",
            [
                "scan",
                str(unreadable),
                "--output=json",
                "--output-file",
                "__REPORT__",
                "--exit-zero",
            ],
            native_bin,
            env,
            report=report,
            expect_success=False,
        )
        malformed = temp_dir / "invalid-containers.yaml"
        malformed.write_text(
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: malformed\nspec:\n  containers: not-a-list\n",
            encoding="utf-8",
        )
        compare_case(
            "nested schema violation",
            ["scan", str(malformed), "--output=json", "--output-file", "__REPORT__"],
            native_bin,
            env,
            report=report,
            expect_success=False,
        )

    print(
        f"Python CLI bridge matches the Rust CLI for {CASE_COUNT} shared contract cases across {len(SUPPORTED_COMMANDS)} command names/aliases."
    )


if __name__ == "__main__":
    main()
