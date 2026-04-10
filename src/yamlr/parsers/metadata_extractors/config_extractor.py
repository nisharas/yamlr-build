#!/usr/bin/env python3
"""
Extractor for ConfigMap/Secret references.

Extracts:
- volumes[].configMap.name
- volumes[].secret.secretName
- env[].valueFrom.configMapKeyRef.name
- envFrom[].configMapRef.name
"""

from __future__ import annotations

from typing import List

from yamlr.models import ManifestIdentity, Shard

__all__ = ["ConfigExtractor"]


from .base_extractor import BaseMetadataExtractor


class ConfigExtractor(BaseMetadataExtractor):
    """Extracts ConfigMap/Secret references from Pod specs."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract ConfigMap/Secret name if in config reference context.

        Returns:
            bool: True if extraction was performed
        """
        if not shard.is_flow_style and key not in ("name", "secretName"):
            return False

        # Volume references
        if "volumes" in path_keys:
            if "configMap" in path_keys and key == "name":
                return ConfigExtractor._apply_list_extraction(shard, key, val, identity, "config_refs")
            if "secret" in path_keys and key == "secretName":
                ConfigExtractor._apply_list_extraction(shard, key, val, identity, "secret_refs")
                return ConfigExtractor._apply_list_extraction(shard, key, val, identity, "secret_volume_refs")

        # Env references
        if key == "name" and ("env" in path_keys or "envFrom" in path_keys):
            if "configMapKeyRef" in path_keys or "configMapRef" in path_keys:
                return ConfigExtractor._apply_list_extraction(shard, key, val, identity, "config_refs")
            if "secretKeyRef" in path_keys or "secretRef" in path_keys:
                return ConfigExtractor._apply_list_extraction(shard, key, val, identity, "secret_refs")

        return False
