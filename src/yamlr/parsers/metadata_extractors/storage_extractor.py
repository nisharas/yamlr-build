#!/usr/bin/env python3
"""
Extractor for StorageClass references.

Extracts:
- PersistentVolumeClaim.spec.storageClassName
"""

from typing import List
from yamlr.models import Shard, ManifestIdentity


class StorageExtractor:
    """Extracts StorageClass references."""
    
    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity
    ) -> bool:
        """
        Extract storageClassName if present in spec.
        """
        if key == "storageClassName":
            if val:
                if val not in identity.storage_class_refs:
                    identity.storage_class_refs.append(val)
            return True
            
        return False
