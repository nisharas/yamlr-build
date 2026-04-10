#!/usr/bin/env python3
"""
Extractor for Cloud-specific metadata (CSI, Cloud Providers).

Extracts:
- PersistentVolume.spec.csi.volumeID
- PersistentVolume.spec.awsElasticBlockStore.volumeID
"""

from __future__ import annotations

from typing import List

from yamlr.models import ManifestIdentity, Shard

from .base_extractor import BaseMetadataExtractor


class CloudExtractor(BaseMetadataExtractor):
    """Extracts Cloud Storage IDs for cross-domain analysis."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard, key: str, val: str, path_keys: List[str], identity: ManifestIdentity
    ) -> bool:
        """Extract volumeID from CSI or EBS blocks."""
        if key == "volumeID" and ("csi" in path_keys or "awsElasticBlockStore" in path_keys):
            # Normalize into the annotation that CrossDomainDetectors expects
            return CloudExtractor._apply_dict_extraction(
                shard, "ebs.csi.aws.com/volume-id", val, identity, "annotations"
            )
        return False
