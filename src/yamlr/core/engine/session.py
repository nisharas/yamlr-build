"""
Yamlr HEAL SESSION
-------------------
Represents a single atomic execution session of the healing engine.

Why: Extracted from engine.py to maintain 100% modularity.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from yamlr.models import HealFileResult, HealStatus

logger = logging.getLogger("yamlr.engine.session")


@dataclass
class HealSession:
    """
    Stateful orchestrator for a healing pass across a set of manifests.

    Responsibilities:
    - Result aggregation
    - Progress tracking
    - Session-level metrics
    """

    workspace_root: str
    results: List[HealFileResult] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    # Session Metrics
    total_files: int = 0
    healed_files: int = 0
    failed_files: int = 0

    def add_result(self, result: HealFileResult):
        """Standard interface for adding results to the session."""
        self.results.append(result)
        self.total_files += 1

        if result.success:
            self.healed_files += 1
        else:
            self.failed_files += 1

    def get_summary(self) -> Dict[str, Any]:
        """Calculates session-level health metrics."""
        duration = time.time() - self.start_time
        return {
            "total": self.total_files,
            "healed": self.healed_files,
            "failed": self.failed_files,
            "duration": round(duration, 2),
            "rate": round(self.total_files / max(duration, 0.1), 1),
        }


def start_new_session(workspace_root: str) -> HealSession:
    """Factory method for creating a fresh session context."""
    return HealSession(workspace_root=workspace_root)
