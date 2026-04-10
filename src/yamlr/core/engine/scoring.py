"""
Yamlr SCORING & DNA
-------------------
Calculates DNA Integrity scores and ranking for Kubernetes manifests.

Why: Extracted from engine.py for 100% modularity and compliance.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("yamlr.engine.scoring")


def calculate_dna_score(result: Any) -> float:
    """
    Computes a DNA Integrity Score (0-100) for a processed file.

    Why: To provide a single 'Health' metric for acquirers and users.
    """
    score = 100.0
    findings = getattr(result, "findings", []) or []

    # [Score-Guard] Critical errors hit the score hardest
    for f in findings:
        sev = getattr(f, "severity", "INFO").upper()
        if sev == "ERROR":
            score -= 40
        elif sev == "WARNING":
            score -= 10
        elif sev == "INFO":
            score -= 2

    # [DNA-Integrity] Factor in successful repairs
    stats = getattr(result, "processing_stats", {}) or {}
    repairs = sum(stats.values()) if isinstance(stats, dict) else 0
    if repairs > 0:
        score += min(repairs, 10.0)  # Bonus for "Healed" state

    return max(0.0, min(100.0, score))


def rank_results(results: List[Any]) -> List[Any]:
    """Sorts results by DNA Integrity (lowest first to highlight issues)."""
    return sorted(results, key=lambda x: getattr(x, "dna_integrity_score", 100))
