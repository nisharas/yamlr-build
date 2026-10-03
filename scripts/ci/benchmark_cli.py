#!/usr/bin/env python3
"""Repeatable end-to-end benchmark for the native YAML scan CLI.

Measures process startup, directory traversal, parsing, validation, and JSON
report generation together. Records raw samples without claiming a universal
latency target from noisy hosted runners.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

MANIFEST = """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: benchmark-config-{index}
  namespace: benchmark
data:
  setting: "enabled"
"""


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil((percentile_value / 100.0) * len(ordered)))
    return ordered[min(rank - 1, len(ordered) - 1)]


def run_scan(
    binary: Path,
    target: Path,
    report: Path,
    expected_exit: int = 0,
    extra_args: list[str] | None = None,
) -> tuple[float, dict[str, Any]]:
    command = [
        str(binary),
        "scan",
        str(target),
        "--output",
        "json",
        "--output-file",
        str(report),
        "--k8s-version",
        "1.30",
        "--no-telemetry",
    ]
    command.extend(extra_args or [])
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        cwd=report.parent,
        timeout=120,
        env={**os.environ, "YAMLR_TELEMETRY": "off", "CI": "true"},
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if completed.returncode != expected_exit:
        raise RuntimeError(
            f"yamlr scan exited {completed.returncode}; expected {expected_exit}: {completed.stderr.strip()}"
        )
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"scan did not produce valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise RuntimeError("scan report must be a JSON object")
    return elapsed_ms, payload


def validate_clean_report(report: dict[str, Any], file_count: int) -> None:
    if report.get("total_files") != file_count:
        raise RuntimeError(
            f"scan counted {report.get('total_files')} files; expected {file_count}"
        )
    if (
        report.get("status") != "passed"
        or report.get("schema_violations") != 0
        or report.get("integrity_violations") != 0
        or report.get("results") != []
    ):
        raise RuntimeError(
            "clean benchmark corpus did not produce a clean, complete report"
        )


def run(
    binary: Path,
    output: Path,
    file_count: int,
    sample_count: int,
    build_profile: str = "unknown",
) -> dict[str, Any]:
    binary = binary.resolve(strict=True)
    if not binary.is_file():
        raise ValueError(f"binary is not a file: {binary}")
    if file_count < 1 or sample_count < 3:
        raise ValueError("files must be positive and samples must be at least 3")

    with TemporaryDirectory(prefix="yamlr-cli-bench-") as temp:
        root = Path(temp)
        corpus = root / "manifests"
        corpus.mkdir()
        for index in range(file_count):
            (corpus / f"config-{index:05}.yaml").write_text(
                MANIFEST.format(index=index), encoding="utf-8"
            )

        # Prove validation is active before timing a clean workload. A scanner
        # which only counts files must not pass this benchmark's fidelity check.
        invalid = root / "invalid-pod.yaml"
        invalid.write_text(
            "apiVersion: v1\nkind: Pod\nmetadata:\n  name: invalid\n",
            encoding="utf-8",
        )
        _, invalid_report = run_scan(
            binary, invalid, root / "fidelity.json", expected_exit=1
        )
        if (
            invalid_report.get("status") != "failed"
            or invalid_report.get("total_files") != 1
            or not isinstance(invalid_report.get("schema_violations"), int)
            or invalid_report["schema_violations"] < 1
            or not isinstance(invalid_report.get("results"), list)
            or not invalid_report["results"]
        ):
            raise RuntimeError("invalid Pod was not reported as a schema violation")

        # Warm caches once, then report the measured samples separately.
        warmup_ms, warmup_report = run_scan(binary, corpus, root / "warmup.json")
        validate_clean_report(warmup_report, file_count)

        samples: list[float] = []
        reports: list[dict[str, Any]] = []
        for index in range(sample_count):
            elapsed_ms, report = run_scan(binary, corpus, root / f"sample-{index}.json")
            validate_clean_report(report, file_count)
            samples.append(elapsed_ms)
            reports.append(report)

    median_ms = statistics.median(samples)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_version": 1,
        "benchmark": "native-cli-directory-scan-json",
        "binary": str(binary),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "build_profile": build_profile,
        "corpus_sha256": hashlib.sha256(
            "".join(MANIFEST.format(index=index) for index in range(file_count)).encode(
                "utf-8"
            )
        ).hexdigest(),
        "k8s_version": "1.30",
        "fidelity_check": "Pod missing required spec rejected with schema findings",
        "warmup_ms": round(warmup_ms, 3),
        "files": file_count,
        "samples": sample_count,
        "latency_ms": {
            "samples": [round(value, 3) for value in samples],
            "median": round(median_ms, 3),
            "p95": round(percentile(samples, 95), 3),
        },
        "throughput_files_per_second_median": round(
            file_count / (median_ms / 1000.0), 2
        ),
        "report": {
            "schema_violations": reports[-1].get("schema_violations"),
            "integrity_violations": reports[-1].get("integrity_violations"),
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
            "github_runner_os": os.environ.get("RUNNER_OS"),
            "git_sha": os.environ.get("GITHUB_SHA"),
        },
    }
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--binary", required=True, type=Path, help="path to built yamlr CLI"
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="JSON artifact output path"
    )
    parser.add_argument("--files", type=int, default=250)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument(
        "--build-profile", choices=["unknown", "debug", "release"], default="unknown"
    )
    args = parser.parse_args()
    try:
        result = run(
            args.binary, args.output, args.files, args.samples, args.build_profile
        )
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"benchmark failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
