"""
Yamlr ENGINE - The High Orchestrator
---------------------------------------
Coordinates the complete healing workflow for Kubernetes manifests.

Why: Refactored to externalize logic into the `yamlr.core.engine` package 
for 100% modularity and compliance with project guardrails.
"""
from yamlr.core.engine.base import YamlrEngine, AuditEngineV3

# Export for backward compatibility
__all__ = ["YamlrEngine", "AuditEngineV3"]
