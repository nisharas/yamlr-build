from __future__ import annotations

__all__ = ["YamlrEngine", "YamlrManager", "HealContext"]


def __getattr__(name: str):
    if name == "YamlrEngine":
        from yamlr.core.engine.base import YamlrEngine

        return YamlrEngine
    if name == "YamlrManager":
        from yamlr.core.manager import YamlrManager

        return YamlrManager
    if name == "HealContext":
        from yamlr.core.context import HealContext

        return HealContext
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
