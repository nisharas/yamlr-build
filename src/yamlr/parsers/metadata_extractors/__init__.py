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

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .annotations_extractor import AnnotationsExtractor
from .cloud_extractor import CloudExtractor
from .config_extractor import ConfigExtractor
from .crd_extractor import CRDExtractor
from .gateway_extractor import GatewayExtractor
from .hpa_extractor import HPAExtractor
from .ingress_extractor import IngressExtractor
from .kms_extractor import KMSExtractor
from .labels_extractor import LabelsExtractor
from .mount_extractor import MountExtractor
from .network_policy_extractor import NetworkPolicyExtractor
from .owner_extractor import OwnerExtractor
from .ports_extractor import PortsExtractor
from .rbac_extractor import RBACExtractor
from .sa_extractor import ServiceAccountExtractor
from .selector_extractor import SelectorExtractor
from .storage_extractor import StorageExtractor
from .volume_extractor import VolumeExtractor
from .vpa_extractor import VPAExtractor

# Global cache for extractor instances to prevent redundant object instantiation.
# Fixes Finding 28.4 (Audit Round 28) - "Silent Killer" instantiation leak.
_EXTRACTOR_CACHE: Optional[List[Any]] = None


def get_extractors():
    """
    Returns all metadata extractors in execution order.
    Uses a global cache to ensure O(1) retrieval without object churn.

    Returns:
        list: List of shared extractor instances
    """
    global _EXTRACTOR_CACHE
    if _EXTRACTOR_CACHE is None:
        _EXTRACTOR_CACHE = [
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
            AnnotationsExtractor(),
            OwnerExtractor(),
            MountExtractor(),
            VPAExtractor(),
            GatewayExtractor(),
            KMSExtractor(),
            CloudExtractor(),
            NetworkPolicyExtractor(),
            CRDExtractor(),
        ]
    return _EXTRACTOR_CACHE


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
    "OwnerExtractor",
    "MountExtractor",
    "VPAExtractor",
    "GatewayExtractor",
    "KMSExtractor",
    "CloudExtractor",
    "CRDExtractor",
]
