#!/usr/bin/env python3
"""
Extractor for KMS (Key Management Service) indicators in Secrets.

Extracts:
- metadata.annotations['kms.key.id']
- metadata.annotations['encryption-key']
- metadata.annotations['sops'] (indicator of encrypted secret)
"""

from __future__ import annotations
from typing import List
from yamlr.models import ManifestIdentity, Shard
__all__ = ['KMSExtractor']


from .base_extractor import BaseMetadataExtractor

class KMSExtractor(BaseMetadataExtractor):
    """Extracts KMS key references or encryption identifiers from Secrets."""

    KMS_ANNOTATIONS = {
        "kms.key.id",
        "encryption-key",
        "aws-kms-key-id",
        "azure-key-vault-url",
        "vault.hashicorp.com/role",
    }

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract KMS metadata from Secret annotations.
        """
        if identity.kind == "Secret":
            if "metadata" in path_keys and "annotations" in path_keys:
                if key.lower() in KMSExtractor.KMS_ANNOTATIONS or "kms" in key.lower():
                    return KMSExtractor._apply_list_extraction(shard, key, val, identity, "kms_key_refs")
        return False
