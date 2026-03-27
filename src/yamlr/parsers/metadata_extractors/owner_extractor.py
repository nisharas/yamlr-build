#!/usr/bin/env python3
"""
Extractor for OwnerReferences.

Extracts:
- metadata.ownerReferences[].kind
- metadata.ownerReferences[].name
"""

from __future__ import annotations
from typing import List
from yamlr.models import ManifestIdentity, Shard
__all__ = ['OwnerExtractor']


from .base_extractor import BaseMetadataExtractor

class OwnerExtractor(BaseMetadataExtractor):
    """Extracts OwnerReferences from metadata."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract OwnerReference if in metadata.ownerReferences context.
        """
        if "ownerReferences" in path_keys:
            if key not in ("kind", "name", "apiVersion", "controller", "blockOwnerDeletion"):
                return False

            if shard.is_list_item:
                if identity.owner_refs is None: identity.owner_refs = []
                identity.owner_refs.append({})

            if not identity.owner_refs:
                identity.owner_refs = [{}]

            identity.owner_refs[-1][key] = val
            return True

        return False
