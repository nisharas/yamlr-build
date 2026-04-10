#!/usr/bin/env python3
"""
Base Metadata Extractor for Yamlr.
----------------------------------
Centralizes common extraction logic (flow-style parsing, identity updates)
to eliminate boilerplate across specialized extractors.

Fixes Finding 28.3 (Audit Round 28).
"""

from __future__ import annotations

from typing import Any

from yamlr.core.utils import parse_flow_style_dict, parse_flow_style_list
from yamlr.models import ManifestIdentity, Shard


class BaseMetadataExtractor:
    """
    Shared utilities for metadata extraction.
    """

    @staticmethod
    def _apply_dict_extraction(shard: Shard, key: str, val: Any, identity: ManifestIdentity, attr_name: str) -> bool:
        """
        Updates a dictionary attribute on ManifestIdentity.
        Handles initialization and flow-style parsing.
        """
        target_dict = getattr(identity, attr_name)
        if target_dict is None:
            target_dict = {}
            setattr(identity, attr_name, target_dict)

        if shard.is_flow_style:
            parsed = parse_flow_style_dict(val)
            if parsed:
                # [FIX] Handle cases where target_dict might be a Proxy
                if hasattr(target_dict, "update"):
                    target_dict.update(parsed)
                else:
                    for k, v in parsed.items():
                        target_dict[k] = v
        else:
            target_dict[key] = val
        return True

    @staticmethod
    def _apply_list_extraction(shard: Shard, key: str, val: Any, identity: ManifestIdentity, attr_name: str) -> bool:
        """
        Updates a list attribute on ManifestIdentity with deduplication.
        Handles initialization and flow-style parsing.
        """
        target_list = getattr(identity, attr_name)
        # Lists in ManifestIdentity are usually default_factory=list, so never None
        if target_list is None:
            target_list = []
            setattr(identity, attr_name, target_list)

        if shard.is_flow_style:
            parsed = parse_flow_style_list(val)
            if parsed:
                # O(N) order-preserving deduplication
                from collections import OrderedDict

                new_items = OrderedDict.fromkeys(item for item in parsed if item not in target_list)
                target_list.extend(new_items.keys())
        else:
            if val not in target_list:
                target_list.append(val)
        return True
