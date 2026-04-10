"""
Yamlr Analysis Rule IDs
-----------------------
Centralized registry of rule identifiers for stable scoring and handling.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Any

from pydantic import BaseModel, Field

class RuleCategory(Enum):
    """Categorization for health and safety rules."""
    SECURITY = "Security"
    AVAILABILITY = "Availability"
    RELIABILITY = "Reliability"
    HYGIENE = "Hygiene"

class RuleMetadata(BaseModel):
    """Declarative metadata for a Yamlr analysis rule."""
    rule_id: str
    category: RuleCategory
    version: str = "1.0.0"
    description: str
    impact: str
    remediation_dna: Optional[str] = None # The DNA fingerprint of the 'perfect' fix

class Rules:
    """Hardened Registry for all Yamlr analysis and safety rules."""
    
    # Constants for Code Stability
    GHOST_SERVICE = "rule/ghost-service"
    ORPHAN_RESOURCE = "rule/orphan-resource"
    BROKEN_VOLUME = "rule/broken-volume"
    PORT_MISMATCH = "rule/port-mismatch"
    INGRESS_BROKEN = "rule/ingress-broken"
    CLOUD_BROKEN = "rule/cloud-broken"
    BROKEN_REFERENCE = "rule/broken-reference"
    BROKEN_REFERENCE_SECRET = "rule/broken-reference-secret"
    GHOST_NETWORK_POLICY = "rule/ghost-network-policy"
    OPA_VIOLATION = "rule/opa-violation"
    SCHEMA_MISMATCH = "rule/schema-mismatch"
    UNSAFE_HOSTPATH = "rule/unsafe-hostpath"
    HOST_NETWORK = "rule/host-network"
    HOST_PID = "rule/host-pid"
    HOST_IPC = "rule/host-ipc"
    ALLOW_PRIVILEGE_ESCALATION = "rule/allow-privilege-escalation"
    SERVICE_NO_SELECTOR = "rule/service-no-selector"
    MISSING_CONFIGMAP_TARGET = "rule/missing-configmap-target"
    INGRESS_TLS_MISSING = "rule/ingress-tls-missing"
    INGRESS_CLASS_MISSING = "rule/ingress-class-missing"
    INGRESS_UNSAFE_ANNOTATION = "rule/ingress-unsafe-annotation"
    INGRESS_INSECURE_TLS = "rule/ingress-insecure-tls"
    INGRESS_WILDCARD_HOST = "rule/ingress-wildcard-host"
    NETWORK_POLICY_MISSING = "rule/network-policy-missing"
    UNTRUSTED_REGISTRY = "rule/untrusted-registry"
    RBAC_WILDCARD = "rule/rbac-wildcard"
    RBAC_PRIVILEGE_ESCALATION = "rule/rbac-privilege-escalation"
    RBAC_SENSITIVE_RESOURCE = "rule/rbac-sensitive-resource"
    RBAC_SUSPICIOUS_BINDING = "rule/rbac-suspicious-binding"
    PRIVILEGED_CONTAINER = "rule/privileged-container"
    DANGEROUS_CAPABILITIES = "rule/dangerous-capabilities"
    RUN_AS_ROOT = "rule/run-as-root"
    SENSITIVE_VOLUME_MOUNT = "rule/sensitive-volume-mount"
    MISSING_NAMESPACE = "rule/missing-namespace"
    IMAGE_TAG_CHECK = "image-tag-check"
    RESOURCE_REQUESTS = "resource-requests"
    RESOURCE_LIMITS = "resource-limits"
    MISSING_LIVENESS = "missing-liveness"
    MISSING_READINESS = "missing-readiness"

    # The "One True Rule Registry"
    METADATA: Dict[str, RuleMetadata] = {
        GHOST_SERVICE: RuleMetadata(
            rule_id=GHOST_SERVICE,
            category=RuleCategory.RELIABILITY,
            description="Service exists but has no backing pods (Selector mismatch).",
            impact="Traffic sent to this service will drop (503), causing downtime.",
            remediation_dna="match-labels-with-deployment"
        ),
        ORPHAN_RESOURCE: RuleMetadata(
            rule_id=ORPHAN_RESOURCE,
            category=RuleCategory.HYGIENE,
            description="Resource exists but is not referenced by any other manifest.",
            impact="Wasted cluster resources and potential security leak.",
        ),
        # ... (Populated further in Phase 8 Audit)
    }

    # Backward Compatibility for Metadata-less calls
    CATEGORIES = {rid: meta.category for rid, meta in METADATA.items()}
    
    @staticmethod
    def get_category(rule_id: str) -> RuleCategory:
        """Returns the category for a given rule ID."""
        meta = Rules.METADATA.get(rule_id)
        if meta:
            return meta.category
        return RuleCategory.HYGIENE

    @staticmethod
    def get_description(rule_id: str) -> str:
        """Returns the human-readable description for a rule."""
        meta = Rules.METADATA.get(rule_id)
        return meta.description if meta else "K8s best practice requirement."
