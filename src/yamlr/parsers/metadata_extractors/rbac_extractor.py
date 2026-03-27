#!/usr/bin/env python3
"""
Extractor for Role and ClusterRole references from RBAC resources.

Extracts:
- RoleBinding.roleRef.name
- ClusterRoleBinding.roleRef.name
"""

from __future__ import annotations
from typing import List
from yamlr.models import Shard, ManifestIdentity
__all__ = ['RBACExtractor']



from .base_extractor import BaseMetadataExtractor

class RBACExtractor(BaseMetadataExtractor):
    """Extracts Role and ClusterRole references from RBAC resources."""
    
    @staticmethod
    def extract_if_applicable(
        shard: Shard,
        key: str,
        val: str,
        path_keys: List[str],
        identity: ManifestIdentity
    ) -> bool:
        """
        Extract Role/ClusterRole name if in RoleBinding/ClusterRoleBinding context.
        """
        if identity.kind not in ("RoleBinding", "ClusterRoleBinding"):
            return False
            
        # Check for roleRef.name
        if key == "name" and "roleRef" in path_keys:
            if identity.kind == "RoleBinding":
                return RBACExtractor._apply_list_extraction(shard, key, val, identity, "role_refs")
            else: # ClusterRoleBinding
                return RBACExtractor._apply_list_extraction(shard, key, val, identity, "cluster_role_refs")
            
        return False
