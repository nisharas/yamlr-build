#!/usr/bin/env python3
"""
Yamlr NAMESPACE HEALER
-----------------------
Enforces explicit namespaces in namespaced resources.
Implements "Smart Inference" to avoid incorrect defaulting.

Author: Antigravity / Yamlr Team
Date: 2026-03-19
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Set

from yamlr.core.context import HealContext

logger = logging.getLogger("yamlr.healers.namespace")

class NamespaceHealer:
    """
    Heals missing namespaces using smart context inference.
    """

    # Cluster-scoped resources that do NOT need a namespace
    CLUSTER_SCOPED = {
        "Namespace", "Node", "ClusterRole", "ClusterRoleBinding",
        "PersistentVolume", "StorageClass", "CustomResourceDefinition",
        "PriorityClass", "RuntimeClass", "VolumeAttachment"
    }

    def __init__(self, enact: bool = True, default_ns: Optional[str] = None):
        self.enact = enact
        self.default_ns = default_ns

    def heal_all(self, context: HealContext):
        """
        Orchestrates namespace healing across all documents.
        """
        if not self.enact or not context.docs:
            return

        # 1. Identify if we have any rule/missing-namespace findings
        targets = [f for f in context.findings if f.rule_id == "rule/missing-namespace"]
        if not targets:
            return

        # 2. Smart Inference: Scan all existing docs for a dominant namespace
        inferred_ns = self._infer_namespace(context.docs)
        
        # Priority: Inferred > Configured Default > Global 'default'
        target_ns = inferred_ns or self.default_ns or "default"

        # 3. Apply fix
        applied_count = 0
        for doc in context.docs:
            kind = doc.get("kind")
            if not kind or kind in self.CLUSTER_SCOPED:
                continue

            metadata = doc.get("metadata")
            if not metadata:
                continue

            if not metadata.get("namespace"):
                metadata["namespace"] = target_ns
                applied_count += 1
                if context:
                    from yamlr.core.stages.boundaries import MutationScope
                    from yamlr.models import HealAction
                    context.prescribe(HealAction(
                        stage="NamespaceHealer",
                        action_type="repair",
                        target=f"{kind}/{metadata.get('name')}.metadata.namespace",
                        description=f"Injected inferred namespace '{target_ns}'",
                        rationale="Resource was missing a namespace and was healed using smart inference from other resources in the same session.",
                        suggestion="Define explicit namespaces to avoid non-deterministic deployment targetting.",
                        severity="info",
                        rule_id="rule/missing-namespace",
                        scope=MutationScope.SPEC_NAMESPACE
                    ))

        if applied_count > 0:
            logger.info(f"NamespaceHealer: Applied '{target_ns}' to {applied_count} resource(s).")

    def _infer_namespace(self, docs: List[Any]) -> Optional[str]:
        """
        Scans all documents to find an existing namespace definition.
        """
        namespaces: Set[str] = set()
        for doc in docs:
            ns = doc.get("metadata", {}).get("namespace")
            if ns:
                namespaces.add(ns)
        
        # If there's exactly one unique namespace used elsewhere, we trust it.
        # If there are multiple, we don't guess (safer to return None).
        if len(namespaces) == 1:
            ns = list(namespaces)[0]
            logger.debug(f"Inferred namespace '{ns}' from existing resources.")
            return ns
            
        return None
