from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("yamlr.healers.metadata")
__all__ = ['MetadataHealer']


class MetadataHealer:
    """
    [Best Practice Healer]
    Ensures metadata safety and operational standards.
    Ported from legacy ShieldEngine.
    """

    def heal_namespace(self, doc: Dict[str, Any], default_namespace: str = "default", context: Optional["HealContext"] = None) -> bool:
        """
        Ensures the resource has a namespace defined if it is namespaced.
        """
        from yamlr.models import CLUSTER_SCOPED_KINDS
        kind = doc.get("kind", "")
        if not kind or kind in CLUSTER_SCOPED_KINDS:
            return False

        if "metadata" not in doc or not isinstance(doc["metadata"], dict):
            doc["metadata"] = {}
            
        metadata = doc["metadata"]
        if "namespace" not in metadata or not metadata["namespace"]:
            metadata["namespace"] = default_namespace
            if context:
                from yamlr.core.stages.boundaries import MutationScope
                from yamlr.models import HealAction
                context.prescribe(HealAction(
                    stage="Shield",
                    action_type="repair",
                    target="metadata.namespace",
                    description=f"Injected missing namespace '{default_namespace}'",
                    rationale="Namespaced resources without an explicit namespace are assigned to 'default', which can lead to accidental leaks between environments.",
                    suggestion=f"Always specify an explicit namespace (e.g., {default_namespace}) for clarity.",
                    severity="info",
                    rule_id="rule/missing-namespace",
                    scope=MutationScope.SPEC_NAMESPACE
                ))
            return True
            
        return False

    def heal_labels(self, doc: Dict[str, Any], required_labels: Dict[str, str], context: Optional["HealContext"] = None) -> bool:
        """
        Injects missing labels into metadata.
        """
        metadata = doc["metadata"]
        if "labels" not in metadata or not isinstance(metadata["labels"], dict):
            metadata["labels"] = {}
            
        labels = metadata["labels"]
        modified = False
        for k, v in required_labels.items():
            if k not in labels:
                labels[k] = v
                modified = True
        
        if modified and context:
            from yamlr.core.stages.boundaries import MutationScope
            from yamlr.models import HealAction
            context.prescribe(HealAction(
                stage="Shield",
                action_type="harden",
                target="metadata.labels",
                description=f"Injected missing required labels: {list(required_labels.keys())}",
                rationale="Required labels are essential for organizational governance and cost-allocation tracking.",
                suggestion="Ensure all manifests include standard organizational labels.",
                severity="info",
                rule_id="rule/required-labels",
                scope=MutationScope.METADATA
            ))
        
        return modified

    def fix_orphans(self, doc: Dict[str, Any], context: Optional["HealContext"] = None) -> bool:
        """
        Moves orphan 'name', 'namespace', or 'labels' keys from the root into 'metadata'.
        
        Why: Standardizes malformed YAML where identity markers are accidentally placed 
             at the root instead of inside the metadata block.
        """
        # [PHASE 6] Support YamlrNode wrappers and raw dicts
        if doc is None:
            return False

        modified = False
        orphan_keys = [k for k in ("name", "namespace", "labels") if k in doc and k != "metadata"]
        
        if not orphan_keys and "metadata" not in doc:
            return False

        if "metadata" not in doc:
            doc["metadata"] = {}
            modified = True

        metadata = doc["metadata"]
        if not isinstance(metadata, dict):
            metadata = {}
            doc["metadata"] = metadata
            modified = True

        for key in ("name", "namespace", "labels"):
            if key in doc and key != "metadata":
                val = doc.pop(key)
                if key not in metadata or not metadata[key]:
                    metadata[key] = val
                    modified = True
                    if context:
                        from yamlr.core.stages.boundaries import MutationScope
                        from yamlr.models import HealAction
                        context.prescribe(HealAction(
                            stage="Shield",
                            action_type="repair",
                            target=f"metadata.{key}",
                            description=f"Structural Cleanup: Migrated orphan '{key}' to metadata",
                            rationale="Kubernetes requires identity markers (name, namespace, labels) to be inside the 'metadata' block.",
                            suggestion=f"Move '{key}' inside the 'metadata' block.",
                            severity="info",
                            rule_id="rule/orphan-metadata",
                            scope=MutationScope.STRUCTURAL
                        ))

        return modified
