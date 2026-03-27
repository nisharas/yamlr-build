#!/usr/bin/env python3
"""
Extractor for ServiceAccount references from Pod specs.

Extracts:
- spec.serviceAccountName (Pod)
- spec.template.spec.serviceAccountName (Deployment/StatefulSet)
"""

from __future__ import annotations
from typing import List

from yamlr.models import ManifestIdentity, Shard
__all__ = ['ServiceAccountExtractor']



from .base_extractor import BaseMetadataExtractor

class ServiceAccountExtractor(BaseMetadataExtractor):
    """Extracts ServiceAccount references from workload resources."""

    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity,
    ) -> bool:
        """
        Extract ServiceAccount name if in Pod/workload spec.

        Returns:
            bool: True if extraction was performed
        """
        # Only extract from workload resources
        valid_kinds = [
            "Pod", "Deployment", "StatefulSet", "DaemonSet",
            "Job", "CronJob", "ReplicaSet",
        ]
        if identity.kind not in valid_kinds:
            return False

        # Check for serviceAccountName in spec
        if key == "serviceAccountName" and "spec" in path_keys:
            if val and not identity.service_account:
                identity.service_account = val
            return True

        return False
