#!/usr/bin/env python3
"""
Extractor for Service/Deployment selectors.

Extracts:
- spec.selector.matchLabels (Deployment/StatefulSet)
- spec.selector (Service)
"""

from __future__ import annotations
from typing import List

from yamlr.models import ManifestIdentity, Shard
__all__ = ['SelectorExtractor']



from .base_extractor import BaseMetadataExtractor

class SelectorExtractor(BaseMetadataExtractor):
    """Extracts selector fields for Service/Deployment matching."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract selector key-value pair if we're in selector context.

        Returns:
            bool: True if extraction was performed
        """
        # Skip structural keys
        if not shard.is_flow_style and key in ("selector", "matchLabels", "spec"):
            return False

        # Check if we're inside spec.selector
        if "spec" in path_keys and "selector" in path_keys:
            return SelectorExtractor._apply_dict_extraction(shard, key, val, identity, "selector")

        return False
