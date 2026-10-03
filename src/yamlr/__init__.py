"""Yamlr: Fast, comment-preserving Kubernetes manifest parser, scanner, and healer."""

import os
from typing import Any, Dict, List, Optional

from yamlr.version import __version__

__all__ = [
    "heal_yaml",
    "scan_yaml",
    "HealResult",
    "generate_default_deny_network_policy",
    "generate_stub",
    "heal_values_yaml",
]

# ---------------------------------------------------------------------------
# Ruff Model Architecture — Preservation Archive Path
# Why: Allows physical archival of all superseded Python modules in `_archive/`
#      while preserving standard Python module discovery for legacy test suites
#      and historical programmatic consumers.
# ---------------------------------------------------------------------------
_archive_dir = os.path.join(os.path.dirname(__file__), "_archive")
if os.path.isdir(_archive_dir) and _archive_dir not in __path__:
    __path__.append(_archive_dir)


class HealResult:
    """Represents the output of a comment-preserving manifest heal operation."""

    def __init__(self, healed_yaml: str, changes: List[str], had_changes: bool):
        self.healed_yaml = healed_yaml
        self.changes = changes
        self.had_changes = had_changes

    def __repr__(self) -> str:
        return f"<HealResult had_changes={self.had_changes} changes_count={len(self.changes)}>"


def heal_yaml(content: str, k8s_version: str = "1.30") -> HealResult:
    """Heal a Kubernetes YAML string in memory with the native Rust engine.

    Why: Provides an in-memory API for programmatic integrations (CI pipelines,
         admission controllers, and developer tooling). Preservation of comments
         and layout depends on the input and the transformations applied.
    """
    import yamlr_native

    if not content or not content.strip():
        return HealResult(healed_yaml=content, changes=[], had_changes=False)

    healed_yaml, changes = yamlr_native.native_heal_yaml(content, k8s_version)
    return HealResult(
        healed_yaml=healed_yaml, changes=changes, had_changes=bool(changes)
    )


def scan_yaml(content: str, k8s_version: str = "1.30") -> Dict[str, Any]:
    """Scans a raw Kubernetes YAML string for schema violations and best practice issues."""
    import yamlr_native

    shards = yamlr_native.native_shard(content)
    manifest = yamlr_native.native_structurize(shards)
    schemas = yamlr_native.native_get_schema_for_version(k8s_version)
    violations = yamlr_native.native_check_schema_violations(content, schemas)
    identity = yamlr_native.extract_native_identity(shards)
    return {
        "identity": {
            "kind": identity.kind if identity else "",
            "name": identity.name if identity else "",
            "namespace": identity.namespace if identity else "",
            "api_version": identity.api_version if identity else "",
        }
        if identity
        else None,
        "violations": [
            {
                "field_path": v.field_path,
                "message": v.message,
                "severity": v.severity,
                "suggested_value": v.suggested_value,
                "line_no": getattr(v, "line_no", 1),
            }
            for v in violations
        ],
        "integrity_violations": [
            {
                "rule_id": iv.rule_id,
                "check_name": iv.check_name,
                "severity": iv.severity,
                "message": iv.message,
                "line_no": iv.line_no,
            }
            for iv in manifest.integrity_violations
        ],
    }


def generate_default_deny_network_policy(namespace: str = "default") -> str:
    """Generates a default-deny NetworkPolicy YAML manifest for a namespace."""
    import yamlr_native

    return yamlr_native.native_generate_default_deny_network_policy(namespace)


def generate_stub(kind: str, name: str, namespace: str = "default") -> str:
    """Generates a missing Kubernetes resource stub YAML manifest."""
    import yamlr_native

    return yamlr_native.native_generate_stub(kind, name, namespace)


def heal_values_yaml(content: str) -> HealResult:
    """Heals a Helm values.yaml file, preserving comments and formatting."""
    import yamlr_native

    if not content or not content.strip():
        return HealResult(healed_yaml=content, changes=[], had_changes=False)

    healed_yaml, changes = yamlr_native.native_heal_values_yaml(content)
    return HealResult(
        healed_yaml=healed_yaml, changes=changes, had_changes=bool(changes)
    )
