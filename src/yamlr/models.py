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

import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


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
    value: Optional[Any] = None
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
    layout_sequence: List[Union[str, Any]] = field(default_factory=list)

    # Pro-Extension: Allows Yamlr to tag shards with intent (e.g., 'SECURITY_ANNOTATION')
    intent_tag: Optional[str] = None


@dataclass
class ManifestIdentity:
    """Represents the discovered 'DNA' of a Kubernetes resource."""

    api_version: Optional[str] = None
    kind: Optional[str] = None
    name: Optional[str] = None
    namespace: Optional[str] = None
    doc_index: int = 0
    was_repaired: bool = False

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
    runtime_class_name: Optional[str] = None  # Pod → RuntimeClass
    crd_group: Optional[str] = None  # CustomResource → CRD (extracted from apiVersion)
    gateway_route_backends: List[Dict[str, str]] = field(
        default_factory=list
    )  # HTTPRoute → Service [{service: "foo", port: "80"}]

    # Deprecation tracking (OSS feature)
    deprecation_info: Optional[Any] = None  # DeprecationInfo from deprecations.py

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

    def to_dict(self) -> dict:
        """
        Serializes the identity object for CLI reporting and API exports.
        """
        return {
            "kind": self.kind,
            "name": self.name,
            "namespace": self.namespace,
            "api_version": self.api_version,
        }


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


class HealConfig(BaseModel):
    """
    The "Execution Contract" for the Yamlr Healing Pipeline.
    Why: Replaces long positional argument lists with a validated schema.
    """
    strict_validation: bool = False
    compact: bool = False
    cluster_version: Optional[str] = "1.31"
    file_path: str = "unknown"
    identity_mode: str = "infer"
    enforce_limits: bool = False
    fix_tags: bool = False
    harden: bool = False
    enforce_probes: bool = False
    enforce_namespace: bool = False
    fast: bool = False
    check_deprecations: bool = False
    fix_refs: bool = False
    allow_unsafe: bool = False
    stub_healing: bool = False
    risk_threshold: Optional[str] = None
    
    # Extra context
    cpu_limit: str = "500m"
    mem_limit: str = "512Mi"
    default_namespace: str = "default"


@dataclass
class SchemaNode:
    """
    [REFERENCE DOCUMENTATION ONLY]

    Defines the expected structure of K8s catalog schemas.
    Currently, catalogs are loaded and used as Dict[str, Any] for flexibility.

    This class serves as documentation for the catalog schema format.
    It is NOT instantiated at runtime in the current implementation.

    Future Enhancement: Could migrate to Pydantic models for runtime validation.
    """

    node_type: str  # 'object', 'array', 'string', 'integer', 'int_or_string'
    fields: Dict[str, "SchemaNode"] = field(default_factory=dict)
    item_type: Optional[str] = None  # For arrays: type of items
    ref: Optional[str] = None  # JSON schema $ref if present


@dataclass
class HealAction:
    """
    Represents a single healing action taken during the pipeline.
    Used for audit trails and detailed reporting.

    Examples:
        - Lexer: Fixed flush-left list at line 23
        - Shield: Added resource limits to container 'web'
        - Validator: Schema validation passed for Deployment/nginx

    Author: Nishar A Sunkesala / Yamlr Team
    Date: 2026-01-26
    """

    stage: str  # Stage that performed the action (e.g., "Lexer", "Shield")
    action_type: str  # Type of action (e.g., "repair", "harden", "validate")
    target: str  # What was modified (e.g., "line 5", "spec.replicas")
    description: str  # Human-readable description
    severity: str = "INFO"  # INFO, WARNING, ERROR

    def to_dict(self) -> dict:
        """Serialize for JSON export."""
        return {
            "stage": self.stage,
            "action_type": self.action_type,
            "target": self.target,
            "description": self.description,
            "severity": self.severity,
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
    findings: List[Dict[str, Any]]
    health_score: int
    identities: List[Dict[str, Any]]
    timestamp: float = field(default_factory=time.time)
    processing_time_seconds: float = 0.0
    written: bool = False
    backup_created: Optional[str] = None
    raw_content: Optional[str] = None
    healed_content: Optional[str] = None
    error: Optional[str] = None
    remediation_command: Optional[str] = None  # New: Command to fix detected issues
    pro_upsell: bool = False
    evidence_receipt: Optional[str] = None
    processing_stats: Optional[Dict[str, Any]] = None
    deprecation_info: Optional[Dict[str, Any]] = None
    _raw_identities: List[Any] = field(default_factory=list, repr=False)
    _source_content: Optional[str] = field(default=None, repr=False)
    raw_content: Optional[str] = field(default=None, repr=False)
    actions: List[Any] = field(default_factory=list)
    reconstruction_depth: str = "Light"

    # Truth-in-Healing Status Gates (Phase 1 Shield)
    phy_status: str = "100%"  # Physical/Lexical (Default success for non-corrupt files)
    kbs_status: str = "0%"    # Kubernetes Schema (Default unknown)
    sem_status: str = "0%"    # Semantic/Reference (Default unknown)

    def to_dict(self) -> Dict[str, Any]:
        """Backward compatibility with dictionary-based reporting."""
        from dataclasses import asdict

        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        """Allows dictionary-style access (e.g., result['status'])."""
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allows dictionary-style assignment (e.g., result['written'] = True)."""
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Allows dictionary-style .get() access."""
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        """Allows 'in' operator check."""
        return hasattr(self, key)
