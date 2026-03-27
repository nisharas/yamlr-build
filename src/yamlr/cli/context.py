"""
Yamlr CLI CONTEXT
-----------------
Environment detection and CLI-specific state management.
"""

from __future__ import annotations
import os
import sys

__all__ = ["YamlrContext", "is_gitops"]
# [DEBUG]
# print(f"DEBUG: context.py loading. ARGOCD_APP_NAME={os.getenv('ARGOCD_APP_NAME')}", file=sys.stderr)

# [Supplier Pivot] GitOps Auto-Detection (Argo CD & Flux)
def is_argocd() -> bool:
    return os.getenv("ARGOCD_APP_NAME") is not None or os.getenv("IS_ARGOCD") == "1"

def is_flux() -> bool:
    return os.getenv("FLUX_KUSTOMIZATION_NAME") is not None or os.getenv("FLUX_HELM_RELEASE_NAME") is not None

def is_gitops() -> bool:
    """
    Returns True if in a GitOps environment or clinical mode.
    """
    return (
        is_argocd() or 
        is_flux() or 
        os.getenv("IS_GITOPS") == "1" or 
        "--clinical" in sys.argv
    )

# Legacy constants for compatibility (using properties in modules is tricky, so we use functions)
IS_ARGOCD = is_argocd()
# Legacy support (deprecated, use functions instead)
# These were causing bugs because they were evaluated at import time
def _get_is_gitops(): return is_gitops()
def _get_is_argocd(): return is_argocd()

def setup_gitops_env() -> str:
    """
    Configures environment variables for clinical GitOps output.
    Returns the target log level.
    """
    if is_gitops():
        os.environ["YAMLR_QUIET"] = "true"
        os.environ["YAMLR_PLAIN"] = "true"
        return "ERROR"
    return os.getenv("YAMLR_LOG_LEVEL", "INFO").upper()

class CliContext:
    """Lazy initialization container for CLI resources."""
    _console = None
    _formatter = None

    @staticmethod
    def get_console(plain=False, target_file=None):
        from yamlr.core.entrypoints.base import get_console
        return get_console(plain=plain, target_file=target_file)

    @classmethod
    def get_formatter(cls):
        if cls._formatter is None:
            from yamlr.ui.formatter import YamlrFormatter
            cls._formatter = YamlrFormatter()
        return cls._formatter
