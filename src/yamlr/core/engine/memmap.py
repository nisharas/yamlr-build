"""
Memmap Manager for Yamlr Engine.

Why: Efficiently shares large data structures (like the K8s catalog)
     across multiprocessing workers without serialization overhead.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import joblib


class MemmapManager:
    """Manages memory-mapped file storage for large Python objects."""

    def __init__(self, runtime_dir: Optional[Path] = None):
        self.runtime_dir = runtime_dir or Path(tempfile.gettempdir()) / "yamlr_memmap"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self._active_maps: Dict[str, str] = {}

    def dump(self, key: str, data: Any) -> str:
        """Dumps data to a memmapped file and returns the path."""
        path = self.runtime_dir / f"{key}.mmap"
        joblib.dump(data, path)
        self._active_maps[key] = str(path)
        return str(path)

    def load(self, path_or_key: str) -> Any:
        """Loads data from a memmapped file."""
        path = self._active_maps.get(path_or_key, path_or_key)
        if not os.path.exists(path):
            return None
        return joblib.load(path, mmap_mode="r")

    def cleanup(self):
        """Removes temporary memmap files."""
        for path in self._active_maps.values():
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        self._active_maps.clear()

    def __del__(self):
        """Safety-net for resource cleanup."""
        self.cleanup()
