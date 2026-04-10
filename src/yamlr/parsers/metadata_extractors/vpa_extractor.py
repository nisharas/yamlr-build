#!/usr/bin/env python3
"""
Extractor for VerticalPodAutoscaler (VPA) targets.

Extracts:
- spec.targetRef.kind
- spec.targetRef.name
"""

from __future__ import annotations

from typing import List

from yamlr.models import ManifestIdentity, Shard

__all__ = ["VPAExtractor"]


from .base_extractor import BaseMetadataExtractor


class VPAExtractor(BaseMetadataExtractor):
    """Extracts target workload from VerticalPodAutoscaler."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract VPA targetRef if in VPA context.
        """
        if identity.kind == "VerticalPodAutoscaler":
            if "targetRef" in path_keys:
                if key in ("kind", "name"):
                    return VPAExtractor._apply_dict_extraction(shard, key, val, identity, "vpa_target")
        return False
