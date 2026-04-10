#!/usr/bin/env python3
"""
Extractor for Pod/Deployment labels.

Extracts:
- metadata.labels (root level or in Pod template)
"""

from __future__ import annotations

from typing import List

from yamlr.models import ManifestIdentity, Shard

__all__ = ["LabelsExtractor"]


from .base_extractor import BaseMetadataExtractor


class LabelsExtractor(BaseMetadataExtractor):
    """Extracts label fields for selector matching."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract label key-value pair if we're in labels context.

        Returns:
            bool: True if extraction was performed
        """
        # Skip structural keys
        if not shard.is_flow_style and key in ("labels", "metadata"):
            return False

        # Must have both 'metadata' and 'labels' in path, but NOT in selector
        if "metadata" in path_keys and "labels" in path_keys and "selector" not in path_keys:
            return LabelsExtractor._apply_dict_extraction(shard, key, val, identity, "labels")

        return False
