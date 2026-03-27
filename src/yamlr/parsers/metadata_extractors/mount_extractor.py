#!/usr/bin/env python3
"""
Extractor for VolumeMounts.

Extracts:
- spec.containers[].volumeMounts[].name
- spec.containers[].volumeMounts[].mountPath
"""

from __future__ import annotations
from typing import List
from yamlr.models import ManifestIdentity, Shard
__all__ = ['MountExtractor']


from .base_extractor import BaseMetadataExtractor

class MountExtractor(BaseMetadataExtractor):
    """Extracts VolumeMount information from Pod specs."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract VolumeMount if in container context.
        """
        if "volumeMounts" in path_keys:
            if key not in ("name", "mountPath", "readOnly", "subPath", "mountPropagation"):
                return False

            if shard.is_list_item:
                if identity.volume_mounts is None: identity.volume_mounts = []
                identity.volume_mounts.append({})

            if not identity.volume_mounts:
                identity.volume_mounts = [{}]

            if key == "name":
                identity.volume_mounts[-1]["name"] = val
            elif key == "mountPath":
                identity.volume_mounts[-1]["path"] = val
            
            return True

        return False
