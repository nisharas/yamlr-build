#!/usr/bin/env python3
"""
Extractor for NetworkPolicy selectors and policy types.

Extracts:
- spec.podSelector.matchLabels
- spec.policyTypes
"""

from __future__ import annotations
from typing import List

from yamlr.models import ManifestIdentity, Shard
__all__ = ['NetworkPolicyExtractor']


from .base_extractor import BaseMetadataExtractor

class NetworkPolicyExtractor(BaseMetadataExtractor):
    """Extracts podSelector and policyTypes for NetworkPolicy matching."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract NetworkPolicy metadata if applicable.

        Returns:
            bool: True if extraction was performed
        """
        if identity.kind != "NetworkPolicy":
            return False

        # 1. Extract spec.podSelector.matchLabels
        if "spec" in path_keys and "podSelector" in path_keys:
            if not shard.is_flow_style and key in ("podSelector", "matchLabels"):
                return False
            return NetworkPolicyExtractor._apply_dict_extraction(shard, key, val, identity, "network_policy_selector")

        # 2. Extract spec.policyTypes
        if "spec" in path_keys and (key == "policyTypes" or "policyTypes" in path_keys):
            return NetworkPolicyExtractor._apply_list_extraction(shard, key, val, identity, "network_policy_types")

        return False
