"""Backward-compatibility facade for core_logic.

Decomposed into discrete sub-modules under yamlr.core.* for modularity.
All public symbols are re-exported here so existing import sites
continue to work unchanged. New code should import directly from
the specific sub-modules instead.

Modules:
    yamlr.core.license          — LicenseManager
    yamlr.core.command_registry  — UniversalCommandRegistry
    yamlr.core.scanner          — streaming_scan, discovery, topology
    yamlr.core.commands         — cmd_dna, cmd_roi, cmd_pulse, cmd_secure, cmd_fleet, cmd_rollback
    yamlr.core.info             — cmd_welcome, cmd_version, cmd_guide_rich, cmd_explain, cmd_completion
    yamlr.core.stages           — SchemaValidationStage, IntegrityAuditStage, TopologyAnalysisStage, HealthScoringStage
    yamlr.core.exceptions       — YamlrError, NativeCoreError, SchemaLoadError, HealingError, LicenseError, DiscoveryError
"""
from yamlr.core.command_registry import UniversalCommandRegistry
from yamlr.core.commands import (
    _record_healing_impact_local,
    cmd_dna,
    cmd_fleet,
    cmd_pulse,
    cmd_roi,
    cmd_rollback,
    cmd_secure,
)
from yamlr.core.exceptions import (
    DiscoveryError,
    HealingError,
    LicenseError,
    NativeCoreError,
    SchemaLoadError,
    YamlrError,
)
from yamlr.core.info import (
    _detect_k8s_version_safe,
    _print_available_topics,
    cmd_completion,
    cmd_explain_universal,
    cmd_guide_rich,
    cmd_version,
    cmd_welcome,
)
from yamlr.core.license import LicenseManager
from yamlr.core.scanner import (
    YAML_EXTENSIONS,
    _calculate_health_score,
    _discover_manifests,
    _process_document_shards,
    _split_and_process_docs,
    audit_topology_outages,
    streaming_scan,
)
from yamlr.core.stages import (
    HealthScoringStage,
    IntegrityAuditStage,
    SchemaValidationStage,
    TopologyAnalysisStage,
)
from yamlr.ui.theme import console  # Re-exported for test mock compatibility

__all__ = [
    "console",
    "LicenseManager", "UniversalCommandRegistry",
    "YAML_EXTENSIONS", "streaming_scan", "audit_topology_outages",
    "_discover_manifests", "_split_and_process_docs",
    "_process_document_shards", "_calculate_health_score",
    "cmd_dna", "cmd_roi", "cmd_pulse", "cmd_secure",
    "cmd_fleet", "cmd_rollback", "_record_healing_impact_local",
    "cmd_welcome", "cmd_version", "cmd_guide_rich",
    "cmd_explain_universal", "cmd_completion",
    "_detect_k8s_version_safe", "_print_available_topics",
    "SchemaValidationStage", "IntegrityAuditStage",
    "TopologyAnalysisStage", "HealthScoringStage",
    "YamlrError", "NativeCoreError", "SchemaLoadError",
    "HealingError", "LicenseError", "DiscoveryError",
    "_collect_yaml_files",
]

# Backwards-compatibility alias
_collect_yaml_files = _discover_manifests
