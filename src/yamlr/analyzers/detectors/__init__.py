#!/usr/bin/env python3
"""
Yamlr CROSS-RESOURCE DETECTORS (FACADE)
---------------------------------------
Facade for specialized detection sub-modules.
Provides backwards compatibility for legacy imports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

# Import from sub-modules
from yamlr.analyzers.detectors.base import build_index
from yamlr.analyzers.detectors.config import detect_broken_refs, detect_orphan_configs
from yamlr.analyzers.detectors.storage import CrossDomainDetectors, detect_broken_volumes
from yamlr.analyzers.detectors.traffic import detect_ghost_services, labels_match
from yamlr.models import ManifestIdentity

__all__ = ["CrossResourceDetectors", "CrossDomainDetectors"]


class CrossResourceDetectors:
    """Facade for K8s resource relationship detection."""

    @staticmethod
    def build_index(identities: List[ManifestIdentity]) -> Dict[str, Dict[str, Set[str]]]:
        return build_index(identities)

    @staticmethod
    def detect_ghost_services(
        services: List[ManifestIdentity],
        workloads: List[ManifestIdentity],
        pro_mode: bool = False,
        graph: Optional[Any] = None,
    ) -> List[Dict]:
        return detect_ghost_services(services, workloads, pro_mode, graph)

    @staticmethod
    def detect_orphan_configs(configs: List[ManifestIdentity], workloads: List[ManifestIdentity]) -> List[Dict]:
        return detect_orphan_configs(configs, workloads)

    @staticmethod
    def detect_broken_volumes(workloads: List[ManifestIdentity], pvcs: List[ManifestIdentity]) -> List[Dict]:
        return detect_broken_volumes(workloads, pvcs)

    @staticmethod
    def detect_broken_refs(
        identities: List[ManifestIdentity], graph: Optional[Any] = None, index: Optional[Dict] = None
    ) -> List[Dict]:
        return detect_broken_refs(identities, graph, index)

    @staticmethod
    def _labels_match(selector: Dict[str, str], labels: Dict[str, str]) -> bool:
        return labels_match(selector, labels)
