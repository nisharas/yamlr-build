#!/usr/bin/env python3
"""
Yamlr MEASUREMENT MODULE
------------------------
Implements the 'Scientific Mode' benchmarking engine.
Allows Yamlr to measure its own performance against a labeled corpus.

Key Metrics:
- Schema HAS: Passes kubectl --validate=strict
- Semantic HAS: No ghost resources / referential orphans
- Lexical HAS: Perfect YAML syntax and normalization

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-21
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("yamlr.core.measurement")
__all__ = ["BenchResult", "CategoryStats", "HealingBenchmarker"]


@dataclass
class BenchResult:
    """Represents the multi-dimensional audit results for a single manifest file.

    Why: To provide a granular, scientific record of detection and healing efficacy.
    """

    file_path: str
    category: str
    detection_success: bool
    schema_has: bool
    semantic_has: bool
    lexical_has: bool
    false_positive: bool
    reconstruction_depth: str = "N/A"  # Light, Medium, Heavy
    processing_time_ms: float = 0.0


@dataclass
class CategoryStats:
    """Aggregated statistics for a specific category of Kubernetes resources.

    Why: To identify structural weaknesses in the healing engine by resource type.
    """

    name: str
    total_files: int = 0
    detected: int = 0
    healed: int = 0  # Passed all HAS dims
    false_positives: int = 0
    avg_depth: Dict[str, int] = field(default_factory=lambda: {"Light": 0, "Medium": 0, "Heavy": 0})

    @property
    def has_score(self) -> float:
        """Calculates the overall Healing Assessment Score (HAS) for this category.

        Why: Key performance indicator for acquisition readiness and product value.
        """
        if self.total_files == 0:
            return 0.0
        return (self.healed / self.total_files) * 100.0


class HealingBenchmarker:
    """
    Orchestrates the scientific audit of a manifest corpus.
    """

    def __init__(self):
        """Initializes the benchmarker with default settings and empty results.

        Why: Prepares the engine for a scientific audit run.
        """
        self.results: List[BenchResult] = []
        self.kubectl_path = "kubectl"
        self._offline_mode = None  # Cache for connectivity
        self.category_map: Dict[str, CategoryStats] = {}

    def _check_connectivity(self) -> bool:
        """Checks if kubectl can reach a cluster (with cache)."""
        if self._offline_mode is not None:
            return not self._offline_mode

        try:
            import subprocess

            # Quick check with short timeout
            # [Security] shell=False is default for list-based args, but making it explicit
            proc = subprocess.run(
                [self.kubectl_path, "version", "--request-timeout=1s"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2,
                shell=False,
            )
            self._offline_mode = proc.returncode != 0
        except (OSError, subprocess.SubprocessError):
            self._offline_mode = True

        return not self._offline_mode

    def verify_via_oracle(self, yaml_content: str) -> bool:
        """
        Validates content using kubectl (if available) or internal fallback.
        """
        if not yaml_content:
            return False

        # 1. Use internal validator if offline
        if not self._check_connectivity():
            from yamlr.core.utils import get_hardened_yaml
            from yamlr.validators.schema_validator import SchemaValidator

            validator = SchemaValidator()
            try:
                # [Security] Use hardened YAML to prevent Billion Laughs (VULN-008)
                hyaml = get_hardened_yaml(typ="safe")
                data = hyaml.load(yaml_content)
                # If it's a list (multi-doc), validate each
                if isinstance(data, list):
                    for doc in data:
                        # If any document fails validation, the whole content fails
                        if validator.validate_full_document(doc):
                            return False
                    return True  # All documents passed
                errors = validator.validate_full_document(data)
                return len(errors) == 0
            except (yaml.YAMLError, AttributeError, TypeError):
                return False

        # 2. Online validation via kubectl
        # [Security] Using list-based arguments to prevent shell injection
        cmd = [self.kubectl_path, "apply", "--dry-run=server", "--validate=strict", "-f", "-"]
        try:
            import subprocess

            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False
            )
            _, _ = proc.communicate(input=yaml_content)
            return proc.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    def record_result(self, result: BenchResult):
        """Records a single benchmark result and updates category-level statistics.

        Why: To build the dataset required for final report generation and telemetry.
        """
        self.results.append(result)

        stats = self.category_map.setdefault(result.category, CategoryStats(name=result.category))
        stats.total_files += 1
        if result.detection_success:
            stats.detected += 1
        if result.schema_has and result.semantic_has and result.lexical_has:
            stats.healed += 1
        if result.false_positive:
            stats.false_positives += 1

        if result.reconstruction_depth in stats.avg_depth:
            stats.avg_depth[result.reconstruction_depth] += 1

    def generate_report(self) -> Dict[str, Any]:
        """
        Generates the final multi-dimensional assessment.
        """
        total = len(self.results)
        if total == 0:
            return {"error": "No results recorded"}

        overall_healed = sum(1 for r in self.results if r.schema_has and r.semantic_has and r.lexical_has)

        # Sort categories by weakest HAS for the 'Top 10 Weakest' report
        sorted_categories = sorted(self.category_map.values(), key=lambda x: x.has_score)

        return {
            "overall_has": (overall_healed / total) * 100.0,
            "total_files": total,
            "category_breakdown": {
                c.name: {
                    "has": c.has_score,
                    "detection_rate": (c.detected / c.total_files * 100) if c.total_files > 0 else 0,
                    "fp_rate": (c.false_positives / c.total_files * 100) if c.total_files > 0 else 0,
                    "depth_distribution": c.avg_depth,
                }
                for c in sorted_categories
            },
            "top_10_weakest": [c.name for c in sorted_categories[:10]],
        }

    def save_to_local_telemetry(self, output_path: str):
        """
        Strictly local NDJSON storage.
        """
        with open(output_path, "w") as f:
            for r in self.results:
                f.write(json.dumps(asdict(r)) + "\n")
        logger.info(f"Local telemetry saved to {output_path}")


class SurgicalTimer:
    """
    Context manager for high-precision surgical timing.

    Why: To provide millisecond-level transparency into engine performance
         bottlenecks across Lexer, Scanner, and Healer phases.
    """

    def __init__(self, name: str, parent: Optional[SurgicalTimer] = None, bootstrap_start: Optional[float] = None):
        self.name = name
        self.start_time: float = 0
        self.bootstrap_start = bootstrap_start
        self.duration_ms: float = 0
        self.bootstrap_ms: float = 0
        self.children: Dict[str, SurgicalTimer] = {}
        self.parent = parent

    def __enter__(self) -> SurgicalTimer:
        self.start_time = time.perf_counter()
        if self.bootstrap_start:
            self.bootstrap_ms = (self.start_time - self.bootstrap_start) * 1000
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000
        if self.parent:
            self.parent.children[self.name] = self

    def get_report(self) -> Dict[str, Any]:
        """Returns a nested timing report."""
        report = {
            "name": self.name,
            "duration_ms": round(self.duration_ms, 2),
            "children": {k: v.get_report() for k, v in self.children.items()},
        }
        if self.bootstrap_ms > 0:
            report["bootstrap_ms"] = round(self.bootstrap_ms, 2)
        return report

    @staticmethod
    def print_timing_report(report: Dict[str, Any], console: Any, indent: int = 0):
        """Prints a human-readable timing tree to the console."""
        prefix = "  " * indent
        name = report["name"]
        duration = report["duration_ms"]

        # Color coding based on latency
        color = "green"
        if duration > 500:
            color = "red"
        elif duration > 100:
            color = "yellow"

        console.print(f"{prefix}• [bold]{name}[/bold]: [{color}]{duration}ms[/{color}]")

        if report.get("bootstrap_ms"):
            b_ms = report["bootstrap_ms"]
            console.print(f"{prefix}  [dim]↳ Bootstrap (Imports/OS): {b_ms}ms[/dim]")

        for child in report["children"].values():
            SurgicalTimer.print_timing_report(child, console, indent + 1)
