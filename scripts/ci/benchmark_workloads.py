#!/usr/bin/env python3
"""Measure representative native workloads and check their results before timing.

Raw local measurements are development evidence, not universal performance budgets.
All generated manifests and mutations are confined to a temporary directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import statistics
import subprocess
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from benchmark_cli import MANIFEST, percentile, run_scan, validate_clean_report

CRD = """apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: widgets.benchmark.yamlr.dev
spec:
  group: benchmark.yamlr.dev
  scope: Namespaced
  names:
    kind: Widget
    plural: widgets
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [replicas]
              properties:
                replicas:
                  type: integer
"""
WIDGET = """apiVersion: benchmark.yamlr.dev/v1
kind: Widget
metadata:
  name: widget-{index}
spec:
  replicas: 2
"""
REPAIR = """# deployment owner: benchmark
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: benchmark
  namespace: benchmark
spec:
  replicas: 2
  selector:
    matchLabels:
      app: benchmark
  template:
    metadata:
      labels:
        app: benchmark
    spec:
      containers:
        - name: benchmark
          image: nginx:1.25.3
"""


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def heal(binary: Path, path: Path) -> float:
    started = time.perf_counter()
    completed = subprocess.run(
        [str(binary), "heal", str(path), "--apply", "--k8s-version", "1.30"],
        cwd=path.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        env={**os.environ, "YAMLR_TELEMETRY": "off", "CI": "true"},
    )
    elapsed = (time.perf_counter() - started) * 1000
    if completed.returncode != 0:
        raise RuntimeError(f"heal exited {completed.returncode}: {completed.stderr}")
    return elapsed


def run(binary: Path, output: Path, documents: int, samples: int, profile: str) -> dict:
    binary = binary.resolve(strict=True)
    binary_sha256 = digest(binary.read_bytes())
    if documents < 2 or samples < 3:
        raise ValueError("documents must be at least 2 and samples at least 3")
    results = []
    with TemporaryDirectory(prefix="yamlr-workloads-") as temporary:
        root = Path(temporary)
        crd = root / "widget-crd.yaml"
        crd.write_text(CRD, encoding="utf-8")
        invalid = root / "invalid-widget.yaml"
        invalid.write_text(
            WIDGET.format(index=0).replace("replicas: 2", 'replicas: "bad"'),
            encoding="utf-8",
        )
        _, report = run_scan(
            binary, invalid, root / "invalid.json", 1, ["--crd", str(crd)]
        )
        if report.get("schema_violations", 0) < 1 or report.get("status") != "failed":
            raise RuntimeError(
                "CRD fidelity failed: wrong nested type was not rejected"
            )

        workloads = [
            (
                "multi-document-scan",
                "---\n".join(MANIFEST.format(index=i) for i in range(documents)),
                [],
            ),
            (
                "custom-resource-scan",
                "---\n".join(WIDGET.format(index=i) for i in range(documents)),
                ["--crd", str(crd)],
            ),
            (
                "heal-clean-crlf",
                ("# retained owner comment\n" + MANIFEST.format(index=0)).replace(
                    "\n", "\r\n"
                ),
                None,
            ),
            ("heal-deprecated-deployment", REPAIR, None),
        ]
        for name, content, scan_args in workloads:
            target = root / "workload.yaml"
            original = content.encode("utf-8")
            if scan_args is not None:
                bad_document = (
                    WIDGET.format(index=documents).replace(
                        "replicas: 2", 'replicas: "bad"'
                    )
                    if scan_args
                    else "apiVersion: v1\nkind: Pod\nmetadata:\n  name: invalid-final-document\n"
                )
                target.write_text(content + "---\n" + bad_document, encoding="utf-8")
                _, fidelity = run_scan(
                    binary, target, root / "stream-fidelity.json", 1, scan_args
                )
                if fidelity.get("schema_violations", 0) < 1:
                    raise RuntimeError(
                        f"{name}: invalid final document was not rejected"
                    )
            timings = []
            warmup = None
            for index in range(samples + 1):
                target.write_bytes(original)
                if scan_args is not None:
                    elapsed, report = run_scan(
                        binary, target, root / "report.json", extra_args=scan_args
                    )
                    validate_clean_report(report, 1)
                    if target.read_bytes() != original:
                        raise RuntimeError(f"{name}: scan modified its input")
                else:
                    elapsed = heal(binary, target)
                    healed = target.read_bytes()
                    if name == "heal-clean-crlf" and healed != original:
                        raise RuntimeError(
                            "clean heal changed comments, content, or CRLF bytes"
                        )
                    if name == "heal-deprecated-deployment":
                        before = yaml.safe_load(content)
                        after = yaml.safe_load(healed)
                        before["apiVersion"] = "apps/v1"
                        annotations = after.get("metadata", {}).get("annotations", {})
                        seal = annotations.pop("yamlr.dev/dna-seal", None)
                        if not isinstance(seal, str) or not re.fullmatch(
                            r"sha256:[0-9a-f]{64}", seal
                        ):
                            raise RuntimeError(
                                "repair did not produce a valid DNA seal"
                            )
                        if not annotations:
                            after["metadata"].pop("annotations", None)
                        if (
                            after != before
                            or b"# deployment owner: benchmark" not in healed
                        ):
                            raise RuntimeError(
                                "repair changed unrelated semantics or removed comment"
                            )
                    heal(binary, target)
                    if target.read_bytes() != healed:
                        raise RuntimeError(f"{name}: healing is not idempotent")
                if index == 0:
                    warmup = elapsed
                else:
                    timings.append(elapsed)
            results.append(
                {
                    "workload": name,
                    "documents": documents if scan_args is not None else 1,
                    "corpus_sha256": digest(original),
                    "warmup_ms": round(warmup, 3),
                    "samples_ms": [round(value, 3) for value in timings],
                    "median_ms": round(statistics.median(timings), 3),
                    "p95_ms": round(percentile(timings, 95), 3),
                    "acceptance": "passed",
                }
            )
    result = {
        "schema_version": 1,
        "benchmark": "native-representative-workloads",
        "binary_sha256": binary_sha256,
        "build_profile": profile,
        "environment": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "git_sha": os.environ.get("GITHUB_SHA"),
        },
        "crd_sha256": digest(CRD.encode()),
        "crd_fidelity": "nested wrong type rejected",
        "workloads": results,
        "limitations": "Single host synthetic development corpus; no memory budget or production latency claim.",
    }
    if digest(binary.read_bytes()) != binary_sha256:
        raise RuntimeError("benchmark executable changed during measurement")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--documents", type=int, default=250)
    parser.add_argument("--samples", type=int, default=31)
    parser.add_argument(
        "--build-profile", choices=["debug", "release", "unknown"], default="unknown"
    )
    args = parser.parse_args()
    result = run(
        args.binary, args.output, args.documents, args.samples, args.build_profile
    )
    for workload in result["workloads"]:
        print(
            f"{workload['workload']}: median {workload['median_ms']} ms, p95 {workload['p95_ms']} ms; acceptance passed"
        )


if __name__ == "__main__":
    main()
