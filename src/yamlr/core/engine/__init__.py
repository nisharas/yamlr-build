"""
Yamlr Engine Package.

Why: To expose the YamlrEngine facade while keeping the implementation modular.
"""
from __future__ import annotations
__all__ = ["YamlrEngine", "AuditEngineV3"]

def __getattr__(name: str):
    if name == "YamlrEngine":
        from yamlr.core.engine.base import YamlrEngine
        return YamlrEngine
    if name == "AuditEngineV3":
        from yamlr.core.engine.base import AuditEngineV3
        return AuditEngineV3
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
