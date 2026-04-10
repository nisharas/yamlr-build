from __future__ import annotations

__all__ = ["setup_platform"]

import io
import multiprocessing
import sys


def setup_platform():
    """Apply platform-specific shims for stability and performance.

    Why: Windows requires special handling for multiprocessing (freeze_support)
         and UTF-8 encoding stability in certain terminal environments.
    """
    if sys.platform == "win32":
        multiprocessing.freeze_support()
        try:
            # [Phase 8] Windows Stability: Enforce 'spawn' to prevent binary-mode crashes
            multiprocessing.set_start_method("spawn", force=True)
        except (RuntimeError, AttributeError):
            pass

        try:
            # Ensure UTF-8 output even if the terminal defaults to CP1252/etc.
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, io.UnsupportedOperation):
            pass

    # Filter out multiprocessing internal flags from sys.argv to prevent
    # accidental parsing by argparse in child processes.
    sys.argv = [arg for arg in sys.argv if not ("parent_pid=" in arg or "--multiprocessing-fork" in arg)]
