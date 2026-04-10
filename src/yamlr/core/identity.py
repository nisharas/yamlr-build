from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

if TYPE_CHECKING:
    from yamlr.core.deprecations import DeprecationInfo

# --- CENTRALIZED RESOURCE REGISTRY ---
# Why: Single source of truth for resource categorization across Lexing, Healing, and Analysis.

# API Version Constants
APPS_V1 = "apps/v1"
BATCH_V1 = "batch/v1"
NETWORKING_V1 = "networking.k8s.io/v1"
RBAC_V1 = "rbac.authorization.k8s.io/v1"
STORAGE_V1 = "storage.k8s.io/v1"
V1 = "v1"

K8S_CORE_KEYS: Set[str] = {
    "kind",
    "apiVersion",
    "metadata",
    "spec",
    "status",
    "selector",
    "template",
    "resources",
    "containers",
    "initContainers",
    "volumes",
    "labels",
    "annotations",
    "data",
    "stringData",
    "ports",
    "env",
    "image",
}

FORCED_ARRAY_FIELDS: Set[str] = {
    "containers",
    "initContainers",
    "ports",
    "env",
    "volumeMounts",
    "volumes",
    "args",
    "command",
    "imagePullSecrets",
    "tolerations",
    "subjects",
    "rules",
    "envFrom",
    "finalizers",
    "ownerReferences",
    "hostAliases",
    "topologySpreadConstraints",
}

SAFE_OBJECT_FIELDS: Set[str] = {
    "metadata",
    "spec",
    "selector",
    "labels",
    "annotations",
    "resources",
    "template",
    "data",
    "stringData",
    "status",
}

SPECIAL_PURPOSE_BLOCKS: Set[str] = {
    "labels",
    "annotations",
    "data",
    "binaryData",
    "stringData",
    "extraArgs",
    "values",
    "set",
    "parameters",
}

WORKLOAD_KINDS: Set[str] = {
    "Deployment",
    "StatefulSet",
    "DaemonSet",
    "Job",
    "CronJob",
    "Pod",
    "ReplicaSet",
    "ReplicationController",
}

CLUSTER_SCOPED_KINDS: Set[str] = {
    "Namespace",
    "Node",
    "ClusterRole",
    "ClusterRoleBinding",
    "StorageClass",
    "PriorityClass",
    "RuntimeClass",
    "PersistentVolume",
    "CustomResourceDefinition",
    "ValidatingWebhookConfiguration",
    "MutatingWebhookConfiguration",
    "CertificateSigningRequest",
    "CSIDriver",
    "CSINode",
    "VolumeAttachment",
    "PodSecurityPolicy",
}

RESOURCE_CATALOG: Dict[str, str] = {
    "Deployment": APPS_V1,
    "StatefulSet": APPS_V1,
    "DaemonSet": APPS_V1,
    "ReplicaSet": APPS_V1,
    "Job": BATCH_V1,
    "CronJob": BATCH_V1,
    "Ingress": NETWORKING_V1,
    "NetworkPolicy": NETWORKING_V1,
    "Service": V1,
    "Pod": V1,
    "Namespace": V1,
    "ConfigMap": V1,
    "Secret": V1,
    "ServiceAccount": V1,
    "PersistentVolumeClaim": V1,
    "PersistentVolume": V1,
    "Role": RBAC_V1,
    "RoleBinding": RBAC_V1,
    "ClusterRole": RBAC_V1,
    "ClusterRoleBinding": RBAC_V1,
    "HorizontalPodAutoscaler": "autoscaling/v2",
    "PodDisruptionBudget": "policy/v1",
    "Lease": "coordination.k8s.io/v1",
    "CertificateSigningRequest": "certificates.k8s.io/v1",
    "CSIDriver": STORAGE_V1,
    "CSINode": STORAGE_V1,
    "VolumeAttachment": STORAGE_V1,
    "PodSecurityPolicy": "policy/v1beta1",
}


@dataclass
class ManifestIdentity:
    """Represents the discovered 'DNA' of a Kubernetes resource.

    Why: To provide a structured identity that remains stable across
         multiple processing rounds (scanning, graph building, healing).
    """

    api_version: Optional[str] = None
    kind: Optional[str] = None
    name: Optional[str] = None
    namespace: Optional[str] = None
    doc_index: int = 0
    was_repaired: bool = False
    file_path: Optional[str] = None

    selector: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None
    config_refs: List[str] = field(default_factory=list)
    secret_refs: List[str] = field(default_factory=list)
    secret_volume_refs: List[str] = field(default_factory=list)
    volume_refs: List[str] = field(default_factory=list)
    service_refs: List[str] = field(default_factory=list)

    container_ports: List[str] = field(default_factory=list)
    service_ports: List[Dict[str, str]] = field(default_factory=list)
    ingress_backends: List[Dict[str, str]] = field(default_factory=list)

    network_policy_selector: Optional[Dict[str, str]] = None
    network_policy_types: List[str] = field(default_factory=list)

    scale_target: Optional[str] = None
    service_account: Optional[str] = None

    role_refs: List[str] = field(default_factory=list)
    cluster_role_refs: List[str] = field(default_factory=list)
    storage_class_refs: List[str] = field(default_factory=list)
    ingress_class_refs: List[str] = field(default_factory=list)
    resource_quota_refs: List[str] = field(default_factory=list)
    limit_range_refs: List[str] = field(default_factory=list)
    hpa_refs: List[str] = field(default_factory=list)

    priority_class_name: Optional[str] = None
    annotations: Dict[str, str] = field(default_factory=dict)
    runtime_class_name: Optional[str] = None
    crd_group: Optional[str] = None
    gateway_route_backends: List[Dict[str, str]] = field(default_factory=list)

    owner_refs: List[Dict[str, str]] = field(default_factory=list)
    volume_mounts: List[Dict[str, str]] = field(default_factory=list)
    vpa_target: Optional[Dict[str, str]] = None
    gateway_class_ref: Optional[str] = None
    kms_key_refs: List[str] = field(default_factory=list)
    crd_versions: List[str] = field(default_factory=list)

    deprecation_info: Optional["DeprecationInfo"] = None

    def is_deprecated(self) -> bool:
        """Why: Strategic check for API obsolescence."""
        return self.deprecation_info is not None

    def is_complete(self) -> bool:
        """Why: Validation gate for schema-aware operations."""
        return bool(self.kind and self.api_version)

    def __str__(self):
        provider = getattr(sys, "_Yamlr_provider", "Yamlr")
        return f"[{provider}] {self.kind or 'Unknown'}/{self.name or 'Unnamed'}"

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ManifestIdentity:
        """Why: Efficient serialization-deserialization for multiprocessing."""
        from dataclasses import fields

        valid_fields = {f.name for f in fields(ManifestIdentity)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        ident = ManifestIdentity(**filtered_data)
        if data.get("is_terraform"):
            ident.is_terraform = True
        return ident

    def to_dict(self) -> dict:
        """Why: Deterministic serialization for reports."""
        from dataclasses import asdict

        data = asdict(self)
        if hasattr(self, "is_terraform"):
            data["is_terraform"] = self.is_terraform
        return dict(sorted(data.items()))
