"""Validate native SARIF serializers offline against the official OASIS schema.

This exercises serializers directly in Rust tests. It does not substitute for
paid CLI entitlement or installed-artifact integration testing.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_SHA256 = "c3b4bb2d6093897483348925aaa73af03b3e3f4bd4ca38cef26dcb4212a2682e"
EXPECTED = {
    "scan-sarif-findings",
    "scan-sarif-clean",
    "scan-sarif-failure",
    "audit-sarif-findings",
    "audit-sarif-clean",
}


def validator() -> jsonschema.Draft4Validator:
    raw = (ROOT / "schemas/sarif-schema-2.1.0.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != SCHEMA_SHA256:
        raise SystemExit("SARIF schema checksum changed; review upstream provenance")
    schema = json.loads(raw)
    jsonschema.Draft4Validator.check_schema(schema)
    return jsonschema.Draft4Validator(schema, format_checker=jsonschema.FormatChecker())


def main() -> None:
    contract = validator()
    completed = subprocess.run(
        [
            "cargo",
            "test",
            "--locked",
            "--manifest-path",
            "native_core/Cargo.toml",
            "--lib",
            "report_contract_fixture",
            "--",
            "--ignored",
            "--nocapture",
            "--test-threads=1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if completed.returncode:
        raise SystemExit(completed.stdout + completed.stderr)
    reports = {}
    for line in completed.stdout.splitlines():
        if "YAMLR_REPORT_CONTRACT:" in line:
            fixture = json.loads(line.split("YAMLR_REPORT_CONTRACT:", 1)[1])
            name = fixture["name"]
            if name in reports:
                raise SystemExit(f"Duplicate report fixture: {name}")
            reports[name] = fixture["report"]
    if reports.keys() != EXPECTED:
        raise SystemExit(f"Report fixture coverage mismatch: {reports.keys()}")
    for name, report in reports.items():
        errors = sorted(contract.iter_errors(report), key=lambda error: str(error.path))
        if errors:
            raise SystemExit(
                f"{name}: "
                + "\n".join(f"{list(error.path)}: {error.message}" for error in errors)
            )
    print(f"Official SARIF schema validation passed for {len(reports)} native reports")


if __name__ == "__main__":
    main()
