#!/usr/bin/env python3
"""
NetworkPolicy Healer - Security Best Practice
---------------------------------------------
Identifies Namespaces (or resources in namespaces) that lack a
default-deny NetworkPolicy and suggests/stubs one.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.healers.best_practices.network_policy")
__all__ = ["NetworkPolicyHealer"]


class NetworkPolicyHealer:
    """Ensures every namespace has a default-deny NetworkPolicy."""

    DEFAULT_DENY_TEMPLATE = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {"name": "default-deny-all", "namespace": "{namespace}"},
        "spec": {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]},
    }

    def heal_docs(
        self,
        docs: List[Dict[str, Any]],
        identities: List[ManifestIdentity],
        harden: bool = False,
        context: Optional[HealContext] = None,
    ) -> int:
        """
        Scans identities for namespaces and checks if a NetworkPolicy exists for them.
        Injects a default-deny policy if missing and stubbing is enabled.

        NOTE: This healer typically runs in the 'Best Practices' stage.
        If stubbing is off, it should only report a finding.
        """
        modified_count = 0

        if not harden:
            return 0

        # 1. Identify all Namespaces (explicit or inferred)
        namespaces = set()
        for ident in identities:
            if ident.kind == "Namespace":
                namespaces.add(ident.name)
            elif ident.namespace:
                namespaces.add(ident.namespace)

        if not namespaces:
            namespaces.add("default")  # Always check default

        # 2. Check which namespaces already have a NetworkPolicy
        protected_namespaces = set()
        for ident in identities:
            if ident.kind == "NetworkPolicy":
                protected_namespaces.add(ident.namespace or "default")

        # 3. For each unprotected namespace, prepare a stub
        for ns in sorted(namespaces):
            if ns not in protected_namespaces:
                logger.debug(f"Namespace '{ns}' has no NetworkPolicy. Suggesting default-deny-all.")

                # Create the policy doc
                policy = self.DEFAULT_DENY_TEMPLATE.copy()
                policy["metadata"] = policy["metadata"].copy()
                policy["metadata"]["namespace"] = ns

                # Add to docs
                docs.append(policy)
                modified_count += 1
                if context:
                    from yamlr.core.stages.boundaries import MutationScope
                    from yamlr.models import HealAction

                    context.prescribe(
                        HealAction(
                            stage="Shield",
                            action_type="harden",
                            target=f"Namespace/{ns}/NetworkPolicy",
                            description=f"Injected default-deny NetworkPolicy for namespace '{ns}'",
                            rationale="A default-deny isolation policy is the foundation of Kubernetes zero-trust networking.",
                            suggestion="Define explicit allow-list policies for required traffic.",
                            severity="warning",
                            rule_id="rule/missing-network-policy",
                            scope=MutationScope.SPEC_NETWORK,
                        )
                    )

        return modified_count
