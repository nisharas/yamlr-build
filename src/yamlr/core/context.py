#!/usr/bin/env python3
"""
Yamlr HEALING CONTEXT
---------------------
A state-management object that acts as the 'Medical Record' for a manifest
undergoing repair. It stores both the raw trauma and the healed structures.

This context is the primary data carrier between the Lexer, Scanner,
and the Surgical Engine.

Enhancements (2026-01-26):
- cluster_version now parameterized (not hardcoded)
- OSS: Manual override via --kube-version flag or Yamlr_KUBE_VERSION env
- Pro: Auto-detection from kubectl/cluster (graceful fallback to OSS)
- Smart defaults based on latest stable K8s version

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-01-26
"""

from __future__ import annotations
import logging
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from yamlr.models import HealAction, ManifestIdentity, Shard
    from yamlr.analyzers.base import AnalysisResult
    from yamlr.core.resource_graph import ResourceGraph

from contextvars import ContextVar
logger = logging.getLogger("yamlr.context")

# [Hardening] Thread-safe session tracking for structured logging
SESSION_ID_VAR: ContextVar[Optional[str]] = ContextVar("yamlr_session_id", default=None)

__all__ = ["HealContext"]


@dataclass
class HealContext:
    """
    Maintains the state of a single manifest repair session.

    Key responsibilities:
    - Hold the original raw text for surgical reference.
    - Store the Shards (lexical units) produced by the Lexer.
    - Track proposed 'Prescriptions' (HealActions) for the manifest.
    - Carry reconstructed document structures for final output.
    - Manage cluster version for accurate deprecation detection.
    """

    # =========================================================================
    # 1. INPUT SOURCE
    # =========================================================================
    raw_text: str
    file_path: Optional[str] = None
    
    # [Hardening] Unique session correlation ID for SRE traceability
    session_id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))
    
    def __post_init__(self):
        """Sets the thread-local session ID for structured logging."""
        SESSION_ID_VAR.set(self.session_id)
    
    # [MODULAR] Primary data carrier for document objects (replaces reconstructed_docs)
    docs: List[Dict[str, Any]] = field(default_factory=list)
    
    # [SAFETY] Track Semantic DNA integrity throughout the pipeline
    dna_integrity: Optional[str] = None
    
    # [MODULAR] Primary diagnostic carrier (replaces logic_logs)
    audit_log: List[str] = field(default_factory=list)
    
    # [MODULAR] Semantic findings collected during pipeline
    findings: List["AnalysisResult"] = field(default_factory=list)

    # [TELEMETRY] Pipeline statistics tracker
    from yamlr.models import PipelineStats
    stats: PipelineStats = field(default_factory=PipelineStats)

    # [PHASE-28] Optimized Execution: Cache findings per document index 
    # to avoid redundant SchemaValidator calls in Stage Eight and Judgment.
    doc_findings: Dict[int, List[Any]] = field(default_factory=dict)

    # [FIX-AUDIT-14] Cached Container context
    _container_cache: List[Dict[str, Any]] = field(default_factory=list, init=False)
    
    @property
    def container_context(self) -> List[Dict[str, Any]]:
        """
        Provides a cached list of all containers (main and init) in the doc set.
        Prevents redundant extraction across Analyzers and Healers.
        """
        if not self._container_cache and self.docs:
            from yamlr.core.k8s_utils import extract_containers
            for doc in self.docs:
                self._container_cache.extend(extract_containers(doc))
        return self._container_cache

    # [HEAL-6.2] Reconstruction Depth (Light, Medium, Heavy)
    depth: str = "Light"

    # =========================================================================
    # 2. LEXICAL STATE
    # =========================================================================
    # List of processed Shard objects (healed lexical units)
    shards: List[Shard] = field(default_factory=list)

    # Reference to the Shadow engine used to capture layout (comments, gaps)
    # This allows Yamlr to preserve human formatting after surgery.
    shadow_engine: Optional[Any] = None

    # [OSS-1] Reference to the Indentation Physicist for layout normalization
    physicist: Optional[Any] = None

    # [PHASE-9] Global workspace context for Relational Surgery
    workspace_identities: List["ManifestIdentity"] = field(default_factory=list)
    config: Optional["HealConfig"] = None
    # =========================================================================
    # The detected primary K8s Kind and API for the current document
    kind: Optional[str] = None
    api_version: Optional[str] = None

    # Complete set of identities for multi-document manifests (separated by ---)
    identities: List[ManifestIdentity] = field(default_factory=list)

    # =========================================================================
    # 4. SURGICAL STATE
    # =========================================================================
    # List of HealAction objects (The 'Prescriptions' for the manifest)
    prescriptions: List[HealAction] = field(default_factory=list)

    # =========================================================================
    # 5. GLOBAL METADATA (ENHANCED: Cluster Version Management)
    # =========================================================================

    # FIXED: cluster_version is now dynamic (not hardcoded to v1.31)
    # Supports:
    # - OSS: Manual override via --kube-version flag or Yamlr_KUBE_VERSION env
    # - Pro: Auto-detection from kubectl/cluster (via bridge)
    # - Fallback: Latest stable K8s version (v1.31 as of 2026-01)
    cluster_version: str = field(
        default_factory=lambda: HealContext._get_default_cluster_version()
    )

    # Legacy Parity: Default namespace for enforcement
    default_namespace: str = "default"

    # Pro feature flag (set by Shield/Validator if Pro is active)
    is_hardened: bool = False

    # Security whitelists (populated from engine/config)
    allowed_host_paths: List[str] = field(default_factory=list)
    trusted_registries: List[str] = field(default_factory=list)
    strict_mode: bool = False

    # [EPIC-23] Safety Engine: Resource dependency graph
    # Built during pipeline after Stage 3 (Identity Extraction).
    # Consumed by analyzers for blast-radius and impact propagation.
    resource_graph: Optional["ResourceGraph"] = None

    # [PHASE-28] Cross-Domain: HCL resource identities for parallel resolution.
    hcl_identities: List[str] = field(default_factory=list)

    # [ROUND-10] Schema Catalog for on-the-fly analyzer instantiation
    catalog: Dict[str, Any] = field(default_factory=dict)

    # =========================================================================
    # 6. DIAGNOSTIC AUDIT TRAIL
    # =========================================================================
    
    # [CLEANUP] Pruned legacy aliases: reconstructed_docs, logic_logs (Finding 28.11)

    # =========================================================================
    # CLUSTER VERSION DETECTION (OSS + Pro)
    # =========================================================================

    # =========================================================================
    # CLUSTER VERSION DETECTION (OSS + Pro)
    # =========================================================================

    @staticmethod
    def _get_default_cluster_version() -> str:
        """
        Intelligently determines the target Kubernetes version.
        Delegates to version_utils for performance.
        """
        from yamlr.core.engine.version_utils import get_default_cluster_version
        return get_default_cluster_version()

    @staticmethod
    def _normalize_version(version: str) -> str:
        """
        Normalizes version string to consistent format.
        Delegates to version_utils.
        """
        from yamlr.core.engine.version_utils import normalize_version
        return normalize_version(version)

    @staticmethod
    def set_cluster_version(version: str) -> str:
        """
        Helper to set cluster version with validation.

        Used by CLI to validate user input before creating context.

        Args:
            version: User-provided version string

        Returns:
            str: Normalized, validated version

        Raises:
            ValueError: If version format is invalid

        Examples:
            >>> HealContext.set_cluster_version("1.28")
            'v1.28'

            >>> HealContext.set_cluster_version("invalid")
            ValueError: Invalid K8s version format
        """
        normalized = HealContext._normalize_version(version)

        # Basic validation: check format vX.Y
        parts = normalized.lstrip("v").split(".")
        if len(parts) < 2:
            raise ValueError(
                f"Invalid Kubernetes version format: '{version}'. "
                f"Expected format: '1.28' or 'v1.31'"
            )

        try:
            int(parts[0])  # Major must be integer
            # Minor may have a suffix (e.g. 31-beta), so we strip non-digits for validation
            minor_clean = re.split(r'[^0-9]', parts[1])[0]
            int(minor_clean)
        except (ValueError, IndexError):
            raise ValueError(
                f"Invalid Kubernetes version: '{version}'. "
                f"Major and minor versions must start with numbers."
            )

        return normalized

    @staticmethod
    def resolve_version_from_api(api_version: str) -> Optional[str]:
        """
        [SURGICAL FIX] Per-File Version Mapping
        Maps an apiVersion to a recommended K8s cluster version for validation.
        """
        if not api_version:
            return None

        # Simple lookup table for major API transitions
        mapping = {
            "apps/v1": "v1.16",
            "networking.k8s.io/v1": "v1.22",
            "networking.k8s.io/v1beta1": "v1.18",
            "policy/v1": "v1.21",
            "policy/v1beta1": "v1.16",
            "autoscaling/v2": "v1.23",
            "batch/v1": "v1.21",
        }

        # Extract base part if it's a sub-version like 'apps/v1'
        return mapping.get(api_version)

    # =========================================================================
    # PUBLIC API: SURGICAL OPERATIONS
    # =========================================================================

    def prescribe(self, action: "HealAction") -> bool:
        """
        Adds a surgical fix to the context if allowed by boundaries.
        
        Returns True if the mutation was accepted, False if blocked by boundary.
        """
        from yamlr.core.stages.boundaries import BoundaryEnforcer
        # [BOUNDARY-ENFORCEMENT] check if this healer-action is allowed
        # Note: We assume a 'default_permit' if none is assigned to the context yet
        permit = getattr(self, "healer_permit", None)
        if permit and not BoundaryEnforcer.validate_mutation(permit, action.scope, self):
             return False

        self.prescriptions.append(action)
        self.add_log(f"Surgery [{action.scope.value.upper()}]: {action.description} at {action.target}")
        
        # [PHASE-9] Propagate prescriptions as findings for reporting
        from yamlr.analyzers.base import AnalysisResult
        self.findings.append(AnalysisResult(
            analyzer_name=action.stage,
            severity=action.severity,
            message=action.description,
            resource_name=action.target,
            resource_kind="Resource", # Broad for now
            file_path=self.file_path,
            rule_id=action.rule_id,
            line_number=0, # Stage level fixes usually affect whole file context
            rationale=action.rationale,
            suggestion=action.suggestion
        ))

    def add_finding(self, finding: "AnalysisResult") -> None:
        """Appends a diagnostic finding to the audit trail."""
        self.findings.append(finding)

    def add_log(self, message: str) -> None:
        """
        Appends a diagnostic message to the audit trail.

        Args:
            message: Log message to record
        """
        self.audit_log.append(message)

    def get_summary(self) -> str:
        """
        Returns a scannable summary of the healing progress.

        Returns:
            str: Human-readable summary

        Example:
            "Manifest: Deployment/nginx | Heals: 3 | Target K8s: v1.28"
        """
        heal_count = len(self.prescriptions)
        return (
            f"Manifest: {self.kind or 'Unknown'} | "
            f"Heals: {heal_count} | "
            f"Target K8s: {self.cluster_version}"
        )

    def get_cluster_info(self) -> dict:
        """
        Returns cluster configuration details.

        Useful for debugging and audit reports.

        Returns:
            dict: Cluster metadata
        """
        return {
            "cluster_version": self.cluster_version,
            "is_hardened": self.is_hardened,
            "detected_kind": self.kind,
            "detected_api": self.api_version,
            "resource_count": len(self.identities),
        }
