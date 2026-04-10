"""
Yamlr AUDITOR HELPERS
-----------------------
Helper functions for cross-resource auditing and reporting.

Why: Extracted from engine.py for 100% modularity and compliance.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

# Leaf-node import to break circularity
from .models import AnalysisResult

logger = logging.getLogger("yamlr.engine.auditor_helpers")


def run_cross_resource_audit(results: List[Any], **kwargs) -> List[AnalysisResult]:
    """
    Performs cross-resource validation across a set of manifests.

    Why: To detect inconsistencies (like orphaned Services, missing PVCs,
         port mismatches, etc.) in the workspace manifest graph.
    """
    try:
        from yamlr.analyzers.registry import AnalyzerRegistry
        from yamlr.analyzers.cross_resource import CrossResourceAnalyzer

        # Find the analyzer instance or class
        cross_analyzer = None
        for inst in AnalyzerRegistry.get_all_analyzers():
            if isinstance(inst, CrossResourceAnalyzer):
                cross_analyzer = inst
                break

        if not cross_analyzer:
            logger.warning("CrossResourceAnalyzer not found in registry. Skipping global audit.")
            return []

        # Execute the global analysis pass
        return cross_analyzer.analyze_batch(results)
    except Exception as e:
        logger.error(f"Global cross-resource audit failed: {e}")
        return []


def detect_manifest_version(content: str, default: str = "1.31") -> str:
    """Extracts target K8s version from the manifest text using regex for maximum speed."""
    import re
    match = re.search(r"target-k8s:\s*([0-9.]+)", content)
    if match:
        return match.group(1).strip()
    return default


def serialize_findings(findings: List[AnalysisResult]) -> List[Dict[str, Any]]:
    """Converts dataclass findings to serializable dicts."""
    return [vars(f) for f in findings]


def build_heal_config(**kwargs) -> HealConfig:
    """Builds a configuration object for the healer pipeline."""
    from .models import HealConfig
    return HealConfig(**kwargs)


def resolve_audit_paths(engine, relative_path: str) -> tuple:
    """Resolves relative path and enforces strict containment within the workspace jail."""
    from pathlib import Path
    from yamlr.core.exceptions import YamlrSecurityError

    workspace_path = Path(getattr(engine, "workspace", ".")).resolve()
    full_path = (workspace_path / relative_path).resolve()

    # [SECURITY] Strict Path Containment (The Jail)
    if not str(full_path).startswith(str(workspace_path)):
        # 🛡️ Emergency Brake: Prevent out-of-bounds healing (LFI/Path Traversal)
        raise YamlrSecurityError(f"Security Violation: Path '{relative_path}' is outside the workspace jail.")

    return full_path, str(full_path)


def check_healing_quota(files_count: int, **kwargs) -> bool:
    """Checks if the user has enough quota for the current operation."""
    from yamlr.core.gatekeeper import ProGate
    return ProGate.check_quota(files_count, is_dry_run=kwargs.get("is_dry_run", False))
