#!/usr/bin/env python3
"""
Extractor for Gateway and GatewayClass references.

Extracts:
- Gateway: spec.gatewayClassName
"""

from __future__ import annotations
from typing import List
from yamlr.models import ManifestIdentity, Shard
__all__ = ['GatewayExtractor']


from .base_extractor import BaseMetadataExtractor

class GatewayExtractor(BaseMetadataExtractor):
    """Extracts GatewayClass references from Gateway resources."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract gatewayClassName if in Gateway spec context.
        """
        if identity.kind == "Gateway":
            if key == "gatewayClassName" and "spec" in path_keys:
                identity.gateway_class_ref = val
                return True
        return False
