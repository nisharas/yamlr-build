from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("yamlr.healers.metadata")

class MetadataHealer:
    """
    [Best Practice Healer]
    Ensures metadata safety and operational standards.
    Ported from legacy ShieldEngine.
    """

    # Cluster-scoped resources (should NOT have a namespace)
    CLUSTER_SCOPED = {
        "Namespace", "Node", "ClusterRole", "ClusterRoleBinding", 
        "StorageClass", "PersistentVolume", "CustomResourceDefinition",
        "PriorityClass", "RuntimeClass", "PV", "CRD"
    }

    def heal_namespace(self, doc: Dict[str, Any], default_namespace: str = "default") -> bool:
        """
        Ensures the resource has a namespace defined if it is namespaced.
        """
        kind = doc.get("kind", "")
        if not kind or kind in self.CLUSTER_SCOPED:
            return False

        if "metadata" not in doc or not isinstance(doc["metadata"], dict):
            doc["metadata"] = {}
            
        metadata = doc["metadata"]
        if "namespace" not in metadata or not metadata["namespace"]:
            metadata["namespace"] = default_namespace
            return True
            
        return False
