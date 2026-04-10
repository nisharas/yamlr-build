#!/usr/bin/env python3
"""
Extractor for PersistentVolumeClaim references.

Extracts:
- volumes[].persistentVolumeClaim.claimName
"""

from __future__ import annotations

from typing import List

from yamlr.models import ManifestIdentity, Shard

__all__ = ["VolumeExtractor"]


from .base_extractor import BaseMetadataExtractor


class VolumeExtractor(BaseMetadataExtractor):
    """Extracts PVC references from Pod specs."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract PVC name if in volume reference context.

        Returns:
            bool: True if extraction was performed
        """
        if not shard.is_flow_style and key != "claimName":
            return False

        if "persistentVolumeClaim" in path_keys:
            return VolumeExtractor._apply_list_extraction(shard, key, val, identity, "volume_refs")

        return False
