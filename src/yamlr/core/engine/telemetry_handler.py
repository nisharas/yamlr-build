from __future__ import annotations

"""
TELEMETRY HANDLER - Engine Analytics Specialist
-----------------------------------------------
Handles the calculation, ranking, and recording of session-level telemetry.

Why: Extracted from base.py and processor_helpers.py to ensure modularity
     and to centralize incident ranking logic.
"""

import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

if TYPE_CHECKING:
    from yamlr.core.engine.base import YamlrEngine
    from yamlr.models import HealFileResult

logger = logging.getLogger("yamlr.engine.telemetry")

# Scoring constants
SEVERITY_RANK: Dict[str, int] = {"error": 100, "warning": 50, "info": 10, "none": 0}
RISK_RANK: Dict[str, int] = {"high": 100, "medium": 50, "low": 10, "none": 0}


def record_file_telemetry(engine: YamlrEngine, res: HealFileResult, relative_path: str, duration: float, **kwargs):
    """Calculates and records telemetry for a single file operation."""
    # Determine bytes processed
    b_proc = 0
    try:
        full_p = engine.workspace / relative_path
        if full_p.exists():
            b_proc = full_p.stat().st_size
    except (OSError, IOError, AttributeError):
        pass

    # Extract stats
    s = getattr(res, "processing_stats", {}) or getattr(res, "stats", {})
    if not isinstance(s, dict):
        s = getattr(s, "__dict__", {}) if hasattr(s, "__dict__") else {}

    fixed = (
        s.get("lexer_repairs", 0)
        + s.get("lexer_typos", 0)
        + s.get("semantic_repairs", 0)
        + s.get("security_hardens", 0)
        + s.get("migrator_changes", 0)
    )

    # Calculate Max Severity & Risk
    max_sev, max_risk = calculate_max_incident_rank(res.findings or [])

    engine.telemetry.record_session(
        files_count=1,
        fixed_issues=fixed,
        avg_dna_score=getattr(res, "trust_score", 100.0),
        is_heal=not kwargs.get("dry_run", True),
        max_severity=max_sev,
        max_risk=max_risk,
        breakdown=s,
        duration_seconds=duration,
        bytes_processed=b_proc,
    )


def calculate_max_incident_rank(findings: list) -> Tuple[str, str]:
    """Calculates the highest severity and risk across all findings."""
    max_sev_label, max_sev_rank = "info", 0
    max_risk_label, max_risk_rank = "low", 0

    for f in findings:
        # Handle both dict and AnalysisResult objects
        sev = (f.get("severity") if isinstance(f, dict) else getattr(f, "severity", "info")) or "info"
        sev = sev.lower()
        rank = SEVERITY_RANK.get(sev, 10)
        if rank > max_sev_rank:
            max_sev_rank, max_sev_label = rank, sev

        risk = (f.get("risk_level") if isinstance(f, dict) else getattr(f, "risk_level", "low")) or "low"
        risk = risk.lower()
        rrank = RISK_RANK.get(risk, 10)
        if rrank > max_risk_rank:
            max_risk_rank, max_risk_label = rrank, risk

    return max_sev_label, max_risk_label


def record_stream_telemetry(engine: YamlrEngine, res: HealFileResult, content: str, duration: float, **kwargs):
    """Calculates and records telemetry for stream operations."""
    b_proc = len(content.encode("utf-8"))

    # Extract stats
    s = getattr(res, "processing_stats", {}) or getattr(res, "stats", {})
    if not isinstance(s, dict):
        s = getattr(s, "__dict__", {}) if hasattr(s, "__dict__") else {}

    fixed = (
        s.get("lexer_repairs", 0)
        + s.get("lexer_typos", 0)
        + s.get("semantic_repairs", 0)
        + s.get("security_hardens", 0)
        + s.get("migrator_changes", 0)
    )

    max_sev, max_risk = calculate_max_incident_rank(res.findings or [])

    engine.telemetry.record_session(
        files_count=1,
        fixed_issues=fixed,
        avg_dna_score=getattr(res, "trust_score", 100.0),
        is_heal=not kwargs.get("dry_run", True),
        max_severity=max_sev,
        max_risk=max_risk,
        breakdown=s,
        duration_seconds=duration,
        bytes_processed=b_proc,
    )


def record_batch_telemetry(engine: YamlrEngine, results: List[HealFileResult], dry_run: bool, start_time: float):
    """Calculates summary metrics and records telemetry for batch operations."""
    total_breakdown, total_fixed, total_score = _aggregate_batch_metrics(results)
    max_sev, max_risk = _calculate_batch_max_ranks(results)

    avg_score = total_score / len(results) if results else 0.0
    duration = time.time() - start_time

    engine.telemetry.record_session(
        files_count=len(results),
        fixed_issues=total_fixed,
        avg_dna_score=avg_score,
        is_heal=not dry_run,
        max_severity=max_sev,
        max_risk=max_risk,
        breakdown=total_breakdown,
        duration_seconds=duration,
        bytes_processed=0,
    )


def _aggregate_batch_metrics(results: List[HealFileResult]) -> Tuple[Dict[str, int], int, float]:
    """Aggregates processing stats across a list of results."""
    breakdown = {
        "lexer_repairs": 0, "lexer_typos": 0, "semantic_repairs": 0,
        "security_hardens": 0, "migrator_changes": 0,
    }
    total_fixed = 0
    total_score = 0.0

    for res in results:
        total_score += getattr(res, "dna_integrity_score", 0) or 0
        s = getattr(res, "processing_stats", None) or {}
        for key in breakdown:
            val = s.get(key, 0)
            breakdown[key] += val
            total_fixed += val

    return breakdown, total_fixed, total_score


def _calculate_batch_max_ranks(results: List[HealFileResult]) -> Tuple[str, str]:
    """Finds the highest severity and risk across all results in a batch."""
    max_sev_label, max_sev_rank = "info", 0
    max_risk_label, max_risk_rank = "low", 0

    for res in results:
        sev, risk = calculate_max_incident_rank(res.findings or [])
        
        s_rank = SEVERITY_RANK.get(sev, 10)
        if s_rank > max_sev_rank:
            max_sev_rank, max_sev_label = s_rank, sev

        r_rank = RISK_RANK.get(risk, 10)
        if r_rank > max_risk_rank:
            max_risk_rank, max_risk_label = r_rank, risk

    return max_sev_label, max_risk_label
