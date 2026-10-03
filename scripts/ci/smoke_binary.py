"""Run a standalone Yamlr binary and verify its scan report."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(
    command: list[str], *, cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )


def main() -> None:
    binary = Path(sys.argv[1]).resolve()
    if not binary.is_file():
        raise SystemExit(f"Standalone binary does not exist: {binary}")

    env = os.environ.copy()
    env["YAMLR_TELEMETRY"] = "off"
    env["CI"] = "true"

    version_result = run([str(binary), "version", "--json"], cwd=binary.parent, env=env)
    version = json.loads(version_result.stdout)
    if not isinstance(version, dict) or not version.get("version"):
        raise SystemExit("Standalone binary did not return structured version metadata")

    with tempfile.TemporaryDirectory(prefix="yamlr-binary-smoke-") as temporary:
        root = Path(temporary)
        manifest = root / "smoke.yaml"
        report = root / "report.json"
        manifest.write_text(
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: smoke\n",
            encoding="utf-8",
        )
        run(
            [
                str(binary),
                "scan",
                str(manifest),
                "--output",
                "json",
                "--output-file",
                str(report),
                "--exit-zero",
            ],
            cwd=root,
            env=env,
        )
        scan_report = json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(scan_report, dict):
            raise SystemExit("Standalone binary did not write a JSON scan report")
        if scan_report.get("total_files") != 1 or not scan_report.get("results"):
            raise SystemExit("Invalid Pod was not scanned and reported with findings")

        # A supplied CRD must not silently lose unsupported validation constraints.
        crd = root / "unsupported-crd.yaml"
        crd.write_text(
            "apiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\n"
            "metadata:\n  name: widgets.example.test\nspec:\n  group: example.test\n"
            "  names:\n    kind: Widget\n  versions:\n    - name: v1\n"
            "      schema:\n        openAPIV3Schema:\n          type: object\n"
            "          properties:\n            spec:\n              type: object\n"
            "              properties:\n                replicas:\n                  type: integer\n"
            "                  minimum: 1\n",
            encoding="utf-8",
        )
        rejected = subprocess.run(
            [
                str(binary),
                "scan",
                str(manifest),
                "--crd",
                str(crd),
                "--output",
                "json",
                "--output-file",
                str(report),
                "--exit-zero",
            ],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        failure = json.loads(report.read_text(encoding="utf-8"))
        if (
            rejected.returncode == 0
            or "Unsupported CRD validation keyword" not in rejected.stderr
            or failure.get("complete") is not False
            or failure.get("status") != "error"
        ):
            raise SystemExit(
                "Unsupported CRD constraints did not produce an incomplete failure report"
            )

        # A supplied CRD must not silently lose unsupported validation constraints.
        crd = root / "unsupported-crd.yaml"
        crd.write_text(
            "apiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\n"
            "metadata:\n  name: widgets.example.test\nspec:\n  group: example.test\n"
            "  names:\n    kind: Widget\n  versions:\n    - name: v1\n"
            "      schema:\n        openAPIV3Schema:\n          type: object\n"
            "          properties:\n            spec:\n              type: object\n"
            "              properties:\n                replicas:\n                  type: integer\n"
            "                  minimum: 1\n",
            encoding="utf-8",
        )
        rejected = subprocess.run(
            [
                str(binary),
                "scan",
                str(manifest),
                "--crd",
                str(crd),
                "--output",
                "json",
                "--output-file",
                str(report),
                "--exit-zero",
            ],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        failure = json.loads(report.read_text(encoding="utf-8"))
        if (
            rejected.returncode == 0
            or "Unsupported CRD validation keyword" not in rejected.stderr
            or failure.get("complete") is not False
            or failure.get("status") != "error"
        ):
            raise SystemExit(
                "Unsupported CRD constraints did not produce an incomplete failure report"
            )

        # json.loads rejects extra documents or metrics on stdout. Exercise
        # the real executable, including its telemetry/output integration.
        for output_format in ("json", "sarif"):
            try:
                completed = run(
                    [
                        str(binary),
                        "scan",
                        str(manifest),
                        "--output",
                        output_format,
                        "--otel",
                        "--exit-zero",
                    ],
                    cwd=root,
                    env=env,
                )
            except subprocess.CalledProcessError as error:
                if (
                    output_format == "sarif"
                    and "requires the paid tier" in error.stderr
                ):
                    print(
                        "SARIF executable smoke requires a paid test entitlement; JSON smoke remains mandatory"
                    )
                    continue
                raise
            payload = json.loads(completed.stdout)
            if output_format == "sarif":
                if (
                    payload.get("version") != "2.1.0"
                    or not payload["runs"][0]["results"]
                ):
                    raise SystemExit(
                        "SARIF scan did not contain the invalid Pod findings"
                    )
            elif payload.get("total_files") != 1 or not payload.get("results"):
                raise SystemExit("JSON stdout report did not contain scan findings")

            manifest.write_bytes(b"\xff\xfe")
            failed = subprocess.run(
                [
                    str(binary),
                    "scan",
                    str(manifest),
                    "--output",
                    output_format,
                    "--exit-zero",
                ],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                timeout=120,
            )
            if failed.returncode == 0:
                raise SystemExit(
                    "Unreadable manifest was incorrectly reported as successful"
                )
            failure = json.loads(failed.stdout)
            if output_format == "sarif":
                if (
                    failure["runs"][0]["invocations"][0]["executionSuccessful"]
                    is not False
                ):
                    raise SystemExit(
                        "Incomplete SARIF scan did not record execution failure"
                    )
            elif (
                failure.get("complete") is not False or failure.get("status") != "error"
            ):
                raise SystemExit(
                    "Incomplete JSON scan did not record execution failure"
                )
            manifest.write_text(
                "apiVersion: v1\nkind: Pod\nmetadata:\n  name: smoke\n",
                encoding="utf-8",
            )

    print(f"Standalone binary smoke passed: {binary.name} ({version['version']})")


if __name__ == "__main__":
    main()
