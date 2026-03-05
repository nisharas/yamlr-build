#!/usr/bin/env python3
"""
Metadata extractors for cross-resource analysis.

These extractors are called by Scanner during the scan_shards() phase
to extract cross-resource references (selectors, labels, config refs, etc.)

Architecture:
- Scanner handles orchestration and path tracking
- Extractors handle specific metadata detection
- Each extractor is 30-50 lines (focused responsibility)

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-01-26
"""

from .config_extractor import ConfigExtractor
from .hpa_extractor import HPAExtractor
from .ingress_extractor import IngressExtractor
from .labels_extractor import LabelsExtractor
from .ports_extractor import PortsExtractor
from .rbac_extractor import RBACExtractor
from .sa_extractor import ServiceAccountExtractor
from .selector_extractor import SelectorExtractor
from .storage_extractor import StorageExtractor
from .volume_extractor import VolumeExtractor


def get_extractors():
    """
    Returns all metadata extractors in execution order.

    Extractors are executed in the order returned here.
    Order doesn't matter much since they check for different patterns.

    Returns:
        list: List of extractor instances
    """
    return [
        SelectorExtractor(),
        LabelsExtractor(),
        ConfigExtractor(),
        VolumeExtractor(),
        IngressExtractor(),
        HPAExtractor(),
        ServiceAccountExtractor(),
        PortsExtractor(),
        RBACExtractor(),
        StorageExtractor(),
    ]


__all__ = [
    "get_extractors",
    "SelectorExtractor",
    "LabelsExtractor",
    "ConfigExtractor",
    "VolumeExtractor",
    "IngressExtractor",
    "HPAExtractor",
    "ServiceAccountExtractor",
    "RBACExtractor",
    "StorageExtractor",
]
