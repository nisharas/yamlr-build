#!/usr/bin/env python3
"""
Extractor for StorageClass references.

Extracts:
- PersistentVolumeClaim.spec.storageClassName
"""

from __future__ import annotations

from typing import List

from yamlr.models import ManifestIdentity, Shard

__all__ = ["StorageExtractor"]


from .base_extractor import BaseMetadataExtractor


class StorageExtractor(BaseMetadataExtractor):
    """Extracts StorageClass references."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard, key: str, val: str, path_keys: List[str], identity: ManifestIdentity
    ) -> bool:
        """
        Extract storageClassName if present in spec.
        """
        if key == "storageClassName":
            return StorageExtractor._apply_list_extraction(shard, key, val, identity, "storage_class_refs")

        return False
