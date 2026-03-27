"""
Yamlr CLI Orchestrator
----------------------
Handles global CLI setup, clinical mode redirection, and logging synchronization.
"""

from __future__ import annotations
import os
import sys
import logging
from typing import Optional

_orig_stdout_fd: Optional[int] = None

def activate_clinical_redirection():
    """Redirects stdout to stderr for clinical/GitOps modes to keep stdout pure for YAML."""
    global _orig_stdout_fd
    if _orig_stdout_fd is not None:
        return
    
    is_clinical = (
        "--clinical" in sys.argv or
        os.getenv("ARGOCD_APP_NAME") is not None or 
        os.getenv("FLUX_KUSTOMIZATION_NAME") is not None or
        os.getenv("YAMLR_QUIET") in ["all", "true"]
    )
    
    if is_clinical:
        try:
            _orig_stdout_fd = os.dup(sys.stdout.fileno())
            os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
            sys.stdout = sys.stderr
            logging.getLogger("yamlr").setLevel(logging.WARNING)
            logging.getLogger("rich").setLevel(logging.WARNING)
            os.environ["YAMLR_QUIET"] = "true"
        except (AttributeError, OSError, IOError):
            pass

def setup_global_logging(level: str):
    """Configures logging for the entire Yamlr CLI."""
    # logging.basicConfig will use sys.stderr
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )
    
    # Preventing propagation to root if necessary
    logger = logging.getLogger("yamlr")
    logger.debug(f"Logging initialized at level {level}")
