
"""
Yamlr Analysis Rule IDs
-----------------------
Centralized registry of rule identifiers for stable scoring and handling.
"""

class Rules:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    # Cross-Resource (Graph) Rules
    GHOST_SERVICE = "rule/ghost-service"
    ORPHAN_RESOURCE = "rule/orphan-resource"
    BROKEN_VOLUME = "rule/broken-volume"
    PORT_MISMATCH = "rule/port-mismatch"
    INGRESS_BROKEN = "rule/ingress-broken"
    
    # OPA Rules
    OPA_VIOLATION = "rule/opa-violation"

    # Schema Rules
    SCHEMA_MISMATCH = "rule/schema-mismatch"
    UNSAFE_HOSTPATH = "rule/unsafe-hostpath"
    HOST_NETWORK = "rule/host-network"
    ALLOW_PRIVILEGE_ESCALATION = "rule/allow-privilege-escalation"
    SERVICE_NO_SELECTOR = "rule/service-no-selector"
    
    # ConfigMap Target Rules
    MISSING_CONFIGMAP_TARGET = "rule/missing-configmap-target"

    # Security Best Practices
    NETWORK_POLICY_MISSING = "rule/network-policy-missing"
    UNTRUSTED_REGISTRY = "rule/untrusted-registry"