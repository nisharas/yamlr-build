"""
Yamlr ENGINE SDK - The Supplier Entry Point
--------------------------------------------
Provides a clean, stable interface for third-party integrations (Supplier Pivot).
This module aggregates the core orchestrators for effortless manifest healing.
"""

from __future__ import annotations

# Direct access to the principal orchestrators
from yamlr.core.engine import YamlrEngine, AuditEngineV3
from yamlr.core.manager import YamlrManager
from yamlr.models import HealConfig, HealFileResult, ManifestIdentity

__all__ = [
    "YamlrEngine",
    "AuditEngineV3",
    "YamlrManager",
    "HealConfig",
    "HealFileResult",
    "ManifestIdentity"
]
