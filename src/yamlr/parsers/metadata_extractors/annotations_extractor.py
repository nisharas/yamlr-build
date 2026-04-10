#!/usr/bin/env python3
"""
Extractor for Kubernetes annotations.

Extracts:
- metadata.annotations (root level)
"""

from __future__ import annotations

from typing import List

from yamlr.models import ManifestIdentity, Shard

__all__ = ["AnnotationsExtractor"]


from .base_extractor import BaseMetadataExtractor


class AnnotationsExtractor(BaseMetadataExtractor):
    """Extracts annotation fields for cross-resource matching."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract annotation key-value pair if we're in annotations context.

        Returns:
            bool: True if extraction was performed
        """
        # Skip structural keys
        if not shard.is_flow_style and key in ("annotations", "metadata"):
            return False

        # Must have both 'metadata' and 'annotations' in path at root level
        if "metadata" in path_keys and "annotations" in path_keys:
            try:
                if path_keys.index("metadata") == 0:
                    return AnnotationsExtractor._apply_dict_extraction(shard, key, val, identity, "annotations")
            except ValueError:
                pass

        return False
