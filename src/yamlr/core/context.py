"""
Yamlr CORE CONTEXT
-------------------
Global execution context, environment detection, and GitOps integration.

Why: Extracted from main/engine to ensure 100% modularity and
     clean separation of concerns.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("yamlr.context")


@dataclass
class HealContext:
    """
    Stateful context for a single healing session.
    Carries configuration, cluster version, and results.
    """

    workspace: str
    catalog: Dict[str, Any]
    cluster_version: str = "1.31"
    dry_run: bool = True
    app_name: str = "Yamlr"
    default_namespace: str = "default"
    strict: bool = False
    compact: bool = False
    emulate: List[str] = field(default_factory=list)
    shadow: bool = False
    original_content: Optional[str] = None # [Phase 17] For atomic revert on regression
    kube_context: Optional[str] = None

    # Session-level state (Forensic Audit Trail)
    findings_count: int = 0
    fixed_count: int = 0
    mutation_count: int = 0  # [Phase 10] Circuit Breaker: Tracks total rule-triggered mutations
    mutation_trace: List[Dict[str, Any]] = field(default_factory=list) # [Phase 16] High-Resolution Audit
    errors: List[str] = field(default_factory=list)
    container_context: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Any] = field(default_factory=list)
    audit_log: List[str] = field(default_factory=list)
    docs: List[Any] = field(default_factory=list)
    config: Any = None # Backward compatibility for healers checking context.config
    quota_exceeded: bool = False

    def audit(self, message: str, level: str = "INFO"):
        """Standardized forensic logging helper.
        
        Why: Enforces a consistent format for all audit entries, making them 
             machine-parsable and human-readable.
        """
        prefix = f"[{level.upper()}]"
        if self.dry_run:
            prefix += "[DRY-RUN]"
        
        log_entry = f"{prefix} {message}"
        self.audit_log.append(log_entry)

    def prescribe(self, action: Any):
        """Standardized method for healers to record a remediation action."""
        self.findings.append(action)
        self.fixed_count += 1
        msg = f"Prescribed: {getattr(action, 'description', 'Mutation')}"
        self.audit(msg, level="INFO")

    def record_action(self, action: Any):
        """Legacy alias for prescribe."""
        self.prescribe(action)

    def check_quota(self) -> bool:
        """Checks if the current session has exceeded the Free Tier quota.
        
        Why: To enforce Tier 0 constraints and protect Pro features. 
             Usage is tracked in .yamlr_runtime/quota.json.
        """
        if os.getenv("YAMLR_INTERNAL_TEST_MODE") == "true" and os.getenv("YAMLR_TEST") != "true":
             return True

        # [REMEDIATION-HARDENING] Check for persistent usage tracking
        from pathlib import Path
        import json
        
        # [QUOTA-HARDENING] Robust path discovery for isolated test environments
        # Why: Pytest and CI/CD pipelines often mock HOME/USERPROFILE.
        try:
            home_dir = os.environ.get("HOME") or os.environ.get("USERPROFILE") or str(Path.home())
            candidates = [
                Path(self.workspace) / ".yamlr_runtime" / "quota.json",
                Path(home_dir) / ".yamlr_runtime" / "quota.json"
            ]
            
            for qf in candidates:
                if qf.exists():
                    try:
                        data = json.loads(qf.read_text())
                        usage = data.get("usage", 0)
                        if usage >= 1000:
                            self.audit_log.append(f"❌ Quota Exceeded (Limit: 1000 manifests). Tracked in: {qf}")
                            self.quota_exceeded = True
                            return False
                    except Exception:
                        continue
        except Exception:
            pass
                
        return True

    @staticmethod
    def _get_default_cluster_version() -> str:
        """Returns the canonical recommended version from the version matrix.
        
        Why: Centralizes default versioning to prevent drift across CLI, 
             Init, and Engine logic.
        """
        from yamlr.core.k8s_versions import MATRIX
        return MATRIX.default_recommended

    @staticmethod
    def set_cluster_version(version: str) -> str:
        """
        Standardizes and validates a Kubernetes version string.
        Returns a clean 'vX.Y' or 'X.Y' string.
        """
        # [Zero-Blindspot] Normalize to X.Y format for catalog lookups
        clean = version.lstrip("vV").strip()
        parts = clean.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return clean


def setup_gitops_env() -> str:
    """
    Detects and configures Yamlr for GitOps environments (ArgoCD, Flux).
    Returns the effective log level.
    """
    is_argocd = os.getenv("ARGOCD_APP_NAME") is not None
    is_flux = os.getenv("FLUX_READY_WAIT") is not None

    if is_argocd or is_flux:
        logger.info(f"🚀 GitOps Environment Detected: {'ArgoCD' if is_argocd else 'Flux'}")
        return os.getenv("YAMLR_LOG_LEVEL", "ERROR")

    return os.getenv("YAMLR_LOG_LEVEL", "INFO")


def is_gitops() -> bool:
    """Returns True if running in a recognized GitOps environment."""
    return os.getenv("ARGOCD_APP_NAME") is not None or os.getenv("FLUX_READY_WAIT") is not None


def is_argocd() -> bool:
    """Returns True if running in ArgoCD."""
    return os.getenv("ARGOCD_APP_NAME") is not None
