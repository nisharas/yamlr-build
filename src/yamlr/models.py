#!/usr/bin/env python3
"""
Yamlr CORE MODELS
--------------------
Defines the fundamental data structures used across the Yamlr engine.
These models represent the "Data Contract" between the Lexer, Shadow, and Scanner.

CNCF Standards Compliance:
- Extensible: Uses metadata dictionaries to allow Enterprise (Pro) data injection.
- Optimized: Uses slots and targeted mutability for high-performance manifest healing.

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-01-21
"""

from __future__ import annotations
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from yamlr.core.deprecations import DeprecationInfo
    from yamlr.parsers.shadow import Gap
    from yamlr.core.stages.boundaries import MutationScope
else:
    # Runtime import to avoid circular dependencies
    from yamlr.core.stages.boundaries import MutationScope

# --- CENTRALIZED RESOURCE REGISTRY ---
# Why: Single source of truth for resource categorization across Lexing, Healing, and Analysis.

# API Version Constants
APPS_V1 = "apps/v1"
BATCH_V1 = "batch/v1"
NETWORKING_V1 = "networking.k8s.io/v1"
RBAC_V1 = "rbac.authorization.k8s.io/v1"
STORAGE_V1 = "storage.k8s.io/v1"
V1 = "v1"

# --- K8S CORE KEYS & SAFETY REGISTRY ---
# Why: Shared across Lexer (heuristics), Scanner (identity), and Healer (schema).

K8S_CORE_KEYS: Set[str] = {
    "kind", "apiVersion", "metadata", "spec", "status", "selector",
    "template", "resources", "containers", "initContainers", "volumes", 
    "labels", "annotations", "data", "stringData", "ports", "env", "image"
}

# Fields that MUST be sequences to prevent corruption in high-trauma docs.
FORCED_ARRAY_FIELDS: Set[str] = {
    "containers", "initContainers", "ports", "env", "volumeMounts", 
    "volumes", "args", "command", "imagePullSecrets", "tolerations",
    "subjects", "rules", "envFrom", "finalizers", "ownerReferences",
    "hostAliases", "topologySpreadConstraints"
}

# Fields that MUST be Maps (CommentedMap).
# Why: Used by Structurer to ensure structural integrity during reconstruction.
SAFE_OBJECT_FIELDS: Set[str] = {
    "metadata", "spec", "selector", "labels", "annotations", 
    "resources", "template", "data", "stringData", "status"
}

# Blocks that can contain arbitrary keys (Freeform/Opaque data).
# Why: Used by Scanner to disable fuzzy matching/typo-fixing in these areas.
# Fixes Finding 28.1 (Audit Round 28) - "Special Block" Redundancy.
SPECIAL_PURPOSE_BLOCKS: Set[str] = {
    "labels", "annotations", "data", "binaryData", "stringData", 
    "extraArgs", "values", "set", "parameters"
}

WORKLOAD_KINDS: Set[str] = {
    "Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", 
    "Pod", "ReplicaSet", "ReplicationController"
}

CLUSTER_SCOPED_KINDS: Set[str] = {
    "Namespace", "Node", "ClusterRole", "ClusterRoleBinding", 
    "StorageClass", "PriorityClass", "RuntimeClass",
    "PersistentVolume", "CustomResourceDefinition", 
    "ValidatingWebhookConfiguration", "MutatingWebhookConfiguration",
    "CertificateSigningRequest", "CSIDriver", "CSINode", 
    "VolumeAttachment", "PodSecurityPolicy"
}

# Maps Kinds to their standard API Groups (Heuristic fallback)
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

__all__ = [
    "Shard", 
    "ManifestIdentity", 
    "PipelineStats", 
    "PipelineCapabilities", 
    "HealConfig", 
    "HealAction", 
    "HealFileResult",
    "WORKLOAD_KINDS",
    "CLUSTER_SCOPED_KINDS",
    "RESOURCE_CATALOG",
    "K8S_CORE_KEYS",
    "FORCED_ARRAY_FIELDS",
    "SAFE_OBJECT_FIELDS",
    "HealStatus",
    "HealResult"
]


@dataclass(slots=True)
class Shard:
    """
    The atomic unit of a Kubernetes manifest.
    A Shard represents a logical line (key-value) and its visual 'intent'.

    The 'layout_sequence' holds Gaps and Comments captured by YamlrShadow,
    allowing for a 1:1 faithful reconstruction of the original human layout.
    """

    line_no: int
    indent: int
    key: str
    value: Optional[Union[str, int, float, bool, Dict[str, Any], List[Any]]] = None
    is_list_item: bool = False
    is_table_continuation: bool = False
    is_block: bool = False
    is_doc_boundary: bool = False
    comment: Optional[str] = None
    raw_line: str = ""
    original_indent: int = 0
    is_flow_style: bool = False

    # layout_sequence stores Gap objects or raw comment strings.
    # We allow mutability here so YamlrShadow can graft layout after Lexing.
    layout_sequence: List[Union[str, "Gap"]] = field(default_factory=list)
    trailing_layout_sequence: List[Union[str, "Gap"]] = field(default_factory=list)

    # Pro-Extension: Allows Yamlr to tag shards with intent (e.g., 'SECURITY_ANNOTATION')
    intent_tag: Optional[str] = None


# [FIX] Merged with definition at line 434 to resolve Audit v34 conflict.


@dataclass
class ManifestIdentity:
    """Represents the discovered 'DNA' of a Kubernetes resource."""

    api_version: Optional[str] = None
    kind: Optional[str] = None
    name: Optional[str] = None
    namespace: Optional[str] = None
    doc_index: int = 0
    was_repaired: bool = False
    file_path: Optional[str] = None

    # Cross-resource tracking (OSS feature)
    selector: Optional[Dict[str, str]] = None  # For Service/Deployment
    labels: Optional[Dict[str, str]] = None  # For Pod/Deployment
    config_refs: List[str] = field(default_factory=list)  # ConfigMap names
    secret_refs: List[str] = field(default_factory=list)  # Secret names
    secret_volume_refs: List[str] = field(default_factory=list)  # Secrets used in volumes
    volume_refs: List[str] = field(default_factory=list)  # PVC names
    service_refs: List[str] = field(default_factory=list)  # Ingress → Service

    # Port & Backend tracking (Legacy Porting)
    container_ports: List[str] = field(default_factory=list)  # ["8080", "http"]
    service_ports: List[Dict[str, str]] = field(
        default_factory=list
    )  # [{"port": "80", "targetPort": "8080"}]
    ingress_backends: List[Dict[str, str]] = field(
        default_factory=list
    )  # [{"service": "foo", "port": "80"}]

    # NetworkPolicy Support
    network_policy_selector: Optional[Dict[str, str]] = None
    network_policy_types: List[str] = field(default_factory=list)

    scale_target: Optional[str] = None  # HPA → Deployment/StatefulSet
    service_account: Optional[str] = None  # Pod → ServiceAccount

    # Extended Phase 2 References
    role_refs: List[str] = field(default_factory=list)  # RoleBinding → Role
    cluster_role_refs: List[str] = field(
        default_factory=list
    )  # ClusterRoleBinding → ClusterRole
    storage_class_refs: List[str] = field(default_factory=list)  # PVC/PV → StorageClass
    ingress_class_refs: List[str] = field(
        default_factory=list
    )  # Ingress → IngressClass
    resource_quota_refs: List[str] = field(default_factory=list)  # Namespace scoped
    limit_range_refs: List[str] = field(default_factory=list)  # Namespace scoped
    hpa_refs: List[str] = field(default_factory=list)  # Targeted by HPAs

    # [EPIC-23] Extended Graph Edge References (Phase 2)
    priority_class_name: Optional[str] = None  # Pod → PriorityClass
    annotations: Dict[str, str] = field(default_factory=dict) # K8s Annotations
    runtime_class_name: Optional[str] = None  # Pod → RuntimeClass
    crd_group: Optional[str] = None  # CustomResource → CRD (extracted from apiVersion)
    gateway_route_backends: List[Dict[str, str]] = field(
        default_factory=list
    )  # HTTPRoute → Service [{service: "foo", port: "80"}]

    # Phase 8: Deep Dependency Coverage
    owner_refs: List[Dict[str, str]] = field(default_factory=list)  # [{kind: "ReplicaSet", name: "..."}]
    volume_mounts: List[Dict[str, str]] = field(default_factory=list)  # [{name: "...", path: "..."}]
    vpa_target: Optional[Dict[str, str]] = None  # {kind: "Deployment", name: "..."}
    gateway_class_ref: Optional[str] = None
    kms_key_refs: List[str] = field(default_factory=list) # For Secret encryption keys

    # Deprecation tracking (OSS feature)
    deprecation_info: Optional["DeprecationInfo"] = None

    def is_deprecated(self) -> bool:
        """Check if this resource uses a deprecated API."""
        return self.deprecation_info is not None

    def is_complete(self) -> bool:
        """Determines if the identity is sufficient for schema-aware healing."""
        return bool(self.kind and self.api_version)

    def __str__(self):
        """Dynamic branding: sys._Yamlr_provider is set by Yamlr on initialization."""
        provider = getattr(sys, "_Yamlr_provider", "Yamlr")
        return f"[{provider}] {self.kind or 'Unknown'}/{self.name or 'Unnamed'}"
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ManifestIdentity:
        """
        Reconstructs a ManifestIdentity from a dictionary.
        
        Why: Enables efficient reconstruction in multiprocessing workers 
             where full objects cannot be easily pickled or passed.
        """
        # [Zero-Blindspot] Use dictionary unpacking with defaults to handle all fields
        from dataclasses import fields
        valid_fields = {f.name for f in fields(ManifestIdentity)}
        
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        ident = ManifestIdentity(**filtered_data)
        
        # Restore meta attributes that are not in the dataclass fields
        if data.get("is_terraform"):
            setattr(ident, "is_terraform", True)
            
        return ident

    def to_dict(self) -> dict:
        """
        Serializes the identity object with sorted keys for sovereign determinism.
        """
        from dataclasses import asdict
        data = asdict(self)
        if hasattr(self, "is_terraform"):
            data["is_terraform"] = getattr(self, "is_terraform")
        return dict(sorted(data.items()))


@dataclass
class PipelineStats:
    """
    Standardized statistics for a single healing pipeline execution.
    Why: To provide sub-millisecond visibility into stage-level performance.
    """
    shards_parsed: int = 0
    docs_count: int = 0
    lexer_repairs: int = 0
    lexer_typos: int = 0
    analyzers_run: int = 0
    migrator_changes: int = 0
    validation_errors: int = 0
    semantic_repairs: int = 0
    security_hardens: int = 0
    timings: Dict[str, float] = field(default_factory=dict)
    stage_timings: Dict[str, float] = field(default_factory=dict) # New: stage-wise breakdown


class HealStatus(str, Enum):
    """
    Why: To provide a deterministic set of outcomes for the healing process,
         enabling consistent error handling and reporting.
    """
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class HealResult:
    """
    Why: To encapsulate the comprehensive results of a single healing pass,
         including mutated content, findings, and telemetry.
    """
    status: HealStatus
    content: str
    logs: List[str]
    dna_integrity_score: int
    trust_score: float = 100.0
    phy_status: str = "100%"
    kbs_status: str = "100%"
    sem_status: str = "100%"
    dna_hash: Optional[str] = None

    identities: List[ManifestIdentity] = field(default_factory=list)
    findings: List[AnalysisResult] = field(default_factory=list)
    stats: PipelineStats = field(default_factory=PipelineStats)
    deprecation_info: List[str] = field(default_factory=list)
    depth: str = "Light"
    error_message: Optional[str] = None
    evidence_receipt: Optional[str] = None
    safety_verdict: str = "N/A"
    safety_messages: List[str] = field(default_factory=list)


class PipelineCapabilities(BaseModel):
    """Represents the resolved enterprise capabilities for a pipeline run."""
    can_heal_cross_resource: bool = False
    can_use_sovereign_sorting: bool = False
    can_use_rust_acceleration: bool = True  # OSS by default
    can_generate_evidence: bool = False
    can_verify_dna: bool = False
    can_run_mcp: bool = False
    can_auto_detect_version: bool = False
    has_unlimited_quota: bool = False


class HealConfig(BaseModel):
    """
    The "Execution Contract" for the Yamlr Healing Pipeline.
    Why: Replaces long positional argument lists with a validated schema.
    """
    skip_repair: bool = True  # Repaired documents only in Pro
    strict_validation: bool = False
    safe_mode: bool = False   # NEW: Block sensitive mutations (Secret/RBAC)
    compact: bool = False
    cluster_version: Optional[str] = "1.31"
    file_path: str = "unknown"
    identity_mode: str = "infer"
    enforce_limits: bool = False
    fix_tags: bool = False
    harden: bool = False
    enforce_probes: bool = False
    enforce_namespace: bool = False
    
    # [Blue Team] Security Hardening & Interlocks
    unrestricted: bool = False   # Bypass safety interlocks (privileged containers, etc.)
    allowed_registries: List[str] = field(default_factory=lambda: ["*.gcr.io", "*.pkg.dev", "*.amazonaws.com", "*.azurecr.io"])
    
    # Truth-in-healing flags
    sovereign: bool = False  # Schema-aware sorting and comment grafting (Pro)
    fast: bool = False       # Native Acceleration (Rust)
    check_deprecations: bool = False
    fix_refs: bool = False
    allow_unsafe: bool = False
    stub_healing: bool = False
    generate_receipts: bool = False
    embed_receipt: bool = False  # NEW: Tail-signs the manifest with DNA receipt
    kind: Optional[str] = None
    api_version: Optional[str] = None
    risk_threshold: Optional[str] = None
    safety_threshold: int = 70  # NEW: Emergency Brake threshold (0-100)
    strict_mode: bool = False   # NEW: Abort healing if any high-severity violations exist
    custom_sort_order: Dict[str, int] = Field(default_factory=dict) # NEW: External priority overrides
    pro_preview: bool = False  # NEW: Simulate Pro healing (dry-run but with Pro logic)
    
    # Extra context
    cpu_limit: str = "500m"
    mem_limit: str = "512Mi"
    default_namespace: Optional[str] = None
    
    # Pro Logic: [Phase 8]
    resource_profiles: Dict[str, Any] = field(default_factory=dict) # Context -> limits
    vpa_targets: List[str] = field(default_factory=list) # List of container names

    
    # Resolved Capabilities
    capabilities: PipelineCapabilities = Field(default_factory=PipelineCapabilities)


# [DEPRECATED] SchemaNode was removed in Round 5 to improve ingestability. 
# K8s catalogs are processed as structural dictionaries for maximum flexibility.


@dataclass
class HealAction:
    """
    Represents a single healing action taken during the pipeline.
    Used for audit trails and detailed reporting.

    Why: Provides a unified data contract for all repairs (lexical or semantic).
    """

    stage: str  # Stage that performed the action (e.g., "Lexer", "Shield")
    action_type: str  # Type of action (e.g., "repair", "harden", "validate")
    target: str  # What was modified (e.g., "line 5", "spec.replicas")
    description: str  # Human-readable description
    severity: str = "INFO"  # INFO, WARNING, ERROR
    rule_id: Optional[str] = None  # Internal rule ID for PRO hints
    message: Optional[str] = None
    rationale: Optional[str] = None
    suggestion: Optional[str] = None
    impact_description: Optional[str] = None
    risk_level: Optional[str] = None
    
    # [HEAL-6.5] Scope enforcement (Merged from legacy definition)
    scope: MutationScope = MutationScope.STRUCTURAL 
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    field: Optional[str] = None
    line_number: Optional[int] = None

    def to_dict(self) -> dict:
        """Serialize for JSON export."""
        return {
            "stage": self.stage,
            "action_type": self.action_type,
            "target": self.target,
            "description": self.description,
            "severity": self.severity,
            "rule_id": self.rule_id,
            "message": self.message,
            "rationale": self.rationale,
            "suggestion": self.suggestion,
            "impact_description": self.impact_description,
            "risk_level": self.risk_level,
            "scope": self.scope.value if hasattr(self.scope, 'value') else str(self.scope),
            "old_value": self.old_value,
            "new_value": self.new_value,
            "field": self.field,
            "line_number": self.line_number
        }


@dataclass(slots=True)
class HealFileResult:
    """
    Standardized result for a single file healing operation.
    Replaces the previous un-typed dictionaries from audit_and_heal_file.
    """

    file_path: str
    full_path: str
    success: bool
    status: str
    kind: str
    logic_logs: List[str]
    findings: List[HealAction]
    dna_integrity_score: int
    identities: List[Dict[str, Any]]
    dna_hash: Optional[str] = None

    timestamp: float = field(default_factory=time.time)
    processing_time_seconds: float = 0.0
    written: bool = False
    backup_created: Optional[str] = None
    raw_content: Optional[str] = None
    healed_content: Optional[str] = None
    error: Optional[str] = None
    remediation_command: Optional[str] = None  # New: Command to fix detected issues
    evidence_receipt: Optional[str] = None
    processing_stats: Optional[Dict[str, Any]] = None
    reconstruction_depth: int = 0  # NEW: Depth of the reconstruction tree
    deprecation_info: Optional[Dict[str, Any]] = None
    identities_raw: List[ManifestIdentity] = field(default_factory=list, repr=False)
    _source_content: Optional[str] = field(default=None, repr=False)

    # Truth-in-Healing Status Gates (Phase 1 Shield)
    phy_status: str = "100%"  # Physical/Lexical (Default success for non-corrupt files)
    kbs_status: str = "0%"    # Kubernetes Schema (Default unknown)
    sem_status: str = "0%"    # Semantic/Reference (Default unknown)
    trust_score: float = 100.0000 # [PRO] Aggregate security/safety score (Rounded to 4 decimals)
    pro_features_triggered: bool = False # [PRO] True if Pro-only fixes were simulated

    def to_dict(self) -> Dict[str, Any]:
        """Backward compatibility with dictionary-based reporting with sovereign determinism."""
        from dataclasses import asdict
        return dict(sorted(asdict(self).items()))

    def __getitem__(self, key: str) -> Union[str, bool, int, float, List[Any], Dict[str, Any], None]:
        """Allows dictionary-style access (e.g., result['status'])."""
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allows dictionary-style assignment (e.g., result['written'] = True)."""
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Allows dictionary-style .get() access."""
        return getattr(self, key, default)

    def calculate_integrity_score(self) -> int:
        """
        Calculates the 0-100 DNA Integrity Score.
        
        Formula:
        - 30% Physical/Structural (Valid YAML)
        - 40% Knowledge/Schema (Valid K8s Resource)
        - 30% Semantic/Referential (Connected & Secure)
        """
        def _parse_pct(val: str) -> float:
            try:
                return float(val.strip('%'))
            except (ValueError, AttributeError):
                return 0.0

        phy = _parse_pct(self.phy_status) * 0.30
        kbs = _parse_pct(self.kbs_status) * 0.40
        sem = _parse_pct(self.sem_status) * 0.30
        
        # Adjust for critical engine errors
        if not self.success or self.status == "FAILED":
             return 0
             
        # Deterministic Rounding (Zero-Blindspot)
        # Why: Prevents non-deterministic truncation across different float implementations.
        score = int(round(phy + kbs + sem))
        self.dna_integrity_score = score
        return score

    def __contains__(self, key: str) -> bool:

        """Allows 'in' operator check."""
        return hasattr(self, key)
