#!/usr/bin/env python3
"""
Extractor for Role and ClusterRole references from RBAC resources.

Extracts:
- RoleBinding.roleRef.name
- ClusterRoleBinding.roleRef.name
"""

from typing import List
from yamlr.models import Shard, ManifestIdentity


class RBACExtractor:
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
            if val:
                if identity.kind == "RoleBinding":
                    if val not in identity.role_refs:
                        identity.role_refs.append(val)
                else: # ClusterRoleBinding
                    if val not in identity.cluster_role_refs:
                        identity.cluster_role_refs.append(val)
            return True
            
        return False
