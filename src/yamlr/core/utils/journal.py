"""
Yamlr Forensic Journal (WAL)
----------------------------
Provides atomic tracking for multi-file mutation batches.

Why: To ensure 'Forensic Sovereignty'—even if the process crashes mid-batch,
     the journal provides a record of which files were targeted and their
     pre-mutation state.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("yamlr.journal")


@dataclass
class JournalEntry:
    path: str
    original_hash: str
    status: str = "PENDING"  # PENDING, DONE, FAILED


class HealJournal:
    """Manages the forensic write-ahead-log for healing operations."""

    def __init__(self, workspace_root: Path):
        self.path = workspace_root / ".yamlr-journal"
        self.entries: Dict[str, JournalEntry] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self.entries[k] = JournalEntry(**v)
            except Exception as e:
                logger.error(f"Journal: Failed to load existing journal: {e}")

    def start_batch(self):
        """Initializes a new batch session."""
        self.entries.clear()
        self._commit()

    def log_pending(self, file_path: str, original_hash: str):
        """Registers a file as about to be mutated."""
        self.entries[file_path] = JournalEntry(path=file_path, original_hash=original_hash, status="PENDING")
        self._commit()

    def mark_done(self, file_path: str):
        """Marks a file mutation as successfully completed and synced."""
        if file_path in self.entries:
            self.entries[file_path].status = "DONE"
            self._commit()

    def mark_failed(self, file_path: str):
        """Marks a file mutation as failed."""
        if file_path in self.entries:
            self.entries[file_path].status = "FAILED"
            self._commit()

    def _commit(self):
        """Writes current state to disk."""
        try:
            data = {k: {"path": v.path, "original_hash": v.original_hash, "status": v.status} for k, v in self.entries.items()}
            self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Journal: Commit failed: {e}")

    def cleanup(self):
        """Removes the journal file after a successful batch."""
        if self.path.exists():
            self.path.unlink()

    def get_incomplete(self) -> List[str]:
        """Returns list of files that did not reach DONE status."""
        return [p for p, e in self.entries.items() if e.status == "PENDING"]
