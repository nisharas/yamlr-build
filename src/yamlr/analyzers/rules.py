
"""
Yamlr Analysis Rule IDs
-----------------------
Centralized registry of rule identifiers for stable scoring and handling.
"""
from __future__ import annotations

from enum import Enum

__all__ = ['Rules', 'RuleCategory']


class RuleCategory(Enum):
    """Categorization for health and safety rules.
    
    Why: To enable multi-dimensional reporting (Security, Availability, etc.) 
         and targeted remediation advice.
    """
    SECURITY = "Security"
    AVAILABILITY = "Availability"
    RELIABILITY = "Reliability"
    HYGIENE = "Hygiene"


class Rules:
    """Centralized registry for all Yamlr analysis and safety rules.
    
    Why: To provide stable, deterministic identifiers for scoring, reporting, and remediation.
    """
    # Cross-Resource (Graph) Rules
    GHOST_SERVICE = "rule/ghost-service"
    ORPHAN_RESOURCE = "rule/orphan-resource"
    BROKEN_VOLUME = "rule/broken-volume"
    PORT_MISMATCH = "rule/port-mismatch"
    INGRESS_BROKEN = "rule/ingress-broken"
    CLOUD_BROKEN = "rule/cloud-broken"
    BROKEN_REFERENCE = "rule/broken-reference"
    BROKEN_REFERENCE_SECRET = "rule/broken-reference-secret"
    GHOST_NETWORK_POLICY = "rule/ghost-network-policy"
    
    # OPA Rules
    OPA_VIOLATION = "rule/opa-violation"

    # Schema Rules
    SCHEMA_MISMATCH = "rule/schema-mismatch"
    UNSAFE_HOSTPATH = "rule/unsafe-hostpath"
    HOST_NETWORK = "rule/host-network"
    HOST_PID = "rule/host-pid"
    HOST_IPC = "rule/host-ipc"
    ALLOW_PRIVILEGE_ESCALATION = "rule/allow-privilege-escalation"
    SERVICE_NO_SELECTOR = "rule/service-no-selector"
    
    # ConfigMap Target Rules
    MISSING_CONFIGMAP_TARGET = "rule/missing-configmap-target"

    # 5. Ingress Security
    INGRESS_TLS_MISSING = "rule/ingress-tls-missing"
    INGRESS_CLASS_MISSING = "rule/ingress-class-missing"
    INGRESS_UNSAFE_ANNOTATION = "rule/ingress-unsafe-annotation"
    INGRESS_INSECURE_TLS = "rule/ingress-insecure-tls"
    INGRESS_WILDCARD_HOST = "rule/ingress-wildcard-host"
    
    # Security Best Practices
    NETWORK_POLICY_MISSING = "rule/network-policy-missing"
    UNTRUSTED_REGISTRY = "rule/untrusted-registry"
    
    # RBAC Security
    RBAC_WILDCARD = "rule/rbac-wildcard"
    RBAC_PRIVILEGE_ESCALATION = "rule/rbac-privilege-escalation"
    RBAC_SENSITIVE_RESOURCE = "rule/rbac-sensitive-resource"
    RBAC_SUSPICIOUS_BINDING = "rule/rbac-suspicious-binding"
    
    # Privilege Escalation Rules
    PRIVILEGED_CONTAINER = "rule/privileged-container"
    DANGEROUS_CAPABILITIES = "rule/dangerous-capabilities"
    RUN_AS_ROOT = "rule/run-as-root"
    SENSITIVE_VOLUME_MOUNT = "rule/sensitive-volume-mount"

    # Compliance Rules
    MISSING_NAMESPACE = "rule/missing-namespace"

    # Best Practices (SSOT Mapping)
    IMAGE_TAG_CHECK = "image-tag-check"
    RESOURCE_REQUESTS = "resource-requests"
    RESOURCE_LIMITS = "resource-limits"
    MISSING_LIVENESS = "missing-liveness"
    MISSING_READINESS = "missing-readiness"

    # Category Mapping
    CATEGORIES = {
        # Reliability
        GHOST_SERVICE: RuleCategory.RELIABILITY,
        ORPHAN_RESOURCE: RuleCategory.HYGIENE,
        BROKEN_VOLUME: RuleCategory.RELIABILITY,
        PORT_MISMATCH: RuleCategory.RELIABILITY,
        INGRESS_BROKEN: RuleCategory.AVAILABILITY,
        CLOUD_BROKEN: RuleCategory.RELIABILITY,
        BROKEN_REFERENCE: RuleCategory.RELIABILITY,
        BROKEN_REFERENCE_SECRET: RuleCategory.SECURITY,
        GHOST_NETWORK_POLICY: RuleCategory.SECURITY,
        
        # Security
        OPA_VIOLATION: RuleCategory.SECURITY,
        UNSAFE_HOSTPATH: RuleCategory.SECURITY,
        HOST_NETWORK: RuleCategory.SECURITY,
        HOST_PID: RuleCategory.SECURITY,
        HOST_IPC: RuleCategory.SECURITY,
        ALLOW_PRIVILEGE_ESCALATION: RuleCategory.SECURITY,
        NETWORK_POLICY_MISSING: RuleCategory.SECURITY,
        UNTRUSTED_REGISTRY: RuleCategory.SECURITY,
        RBAC_WILDCARD: RuleCategory.SECURITY,
        RBAC_PRIVILEGE_ESCALATION: RuleCategory.SECURITY,
        RBAC_SENSITIVE_RESOURCE: RuleCategory.SECURITY,
        RBAC_SUSPICIOUS_BINDING: RuleCategory.SECURITY,
        PRIVILEGED_CONTAINER: RuleCategory.SECURITY,
        DANGEROUS_CAPABILITIES: RuleCategory.SECURITY,
        RUN_AS_ROOT: RuleCategory.SECURITY,
        SENSITIVE_VOLUME_MOUNT: RuleCategory.SECURITY,
        INGRESS_TLS_MISSING: RuleCategory.SECURITY,
        INGRESS_CLASS_MISSING: RuleCategory.SECURITY,
        INGRESS_UNSAFE_ANNOTATION: RuleCategory.SECURITY,
        INGRESS_INSECURE_TLS: RuleCategory.SECURITY,
        INGRESS_WILDCARD_HOST: RuleCategory.SECURITY,
        
        # Availability
        SCHEMA_MISMATCH: RuleCategory.AVAILABILITY,
        MISSING_LIVENESS: RuleCategory.AVAILABILITY,
        MISSING_READINESS: RuleCategory.AVAILABILITY,
        SERVICE_NO_SELECTOR: RuleCategory.AVAILABILITY,
        
        # Hygiene
        MISSING_CONFIGMAP_TARGET: RuleCategory.HYGIENE,
        MISSING_NAMESPACE: RuleCategory.HYGIENE,
        IMAGE_TAG_CHECK: RuleCategory.HYGIENE,
        RESOURCE_REQUESTS: RuleCategory.RELIABILITY,
        RESOURCE_LIMITS: RuleCategory.RELIABILITY,
    }

    @staticmethod
    def get_category(rule_id: str) -> RuleCategory:
        """Returns the category for a given rule ID."""
        return Rules.CATEGORIES.get(rule_id, RuleCategory.HYGIENE)
