#!/usr/bin/env python3
"""
Extractor for CustomResourceDefinition (CRD) versioning.

Extracts:
- spec.versions[].name (CRD)
- spec.group (CRD)
"""

from __future__ import annotations

from typing import List

from yamlr.models import ManifestIdentity, Shard

from .base_extractor import BaseMetadataExtractor

__all__ = ["CRDExtractor"]


class CRDExtractor(BaseMetadataExtractor):
    """Extracts version names and groups from CustomResourceDefinitions."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract versions from a CRD manifest.

        Returns:
            bool: True if extraction was performed
        """
        if identity.kind != "CustomResourceDefinition":
            return False

        # Extract group for correlation
        if key == "group" and "spec" in path_keys:
            identity.crd_group = str(val) if val else None
            return True

        # Extract versions from spec.versions list
        if key == "name" and "versions" in path_keys and "spec" in path_keys:
            if val and val not in identity.crd_versions:
                identity.crd_versions.append(str(val))
            return True

        return False
